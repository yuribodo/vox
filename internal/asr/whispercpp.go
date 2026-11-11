package asr

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	voxaudio "github.com/yuribodo/vox/internal/audio"
)

type WhisperCPPConfig struct {
	Binary   string
	Model    string
	VADModel string
	Language string
	Threads  int
	UseGPU   bool
	// Server returns a ready whisper-server base URL, or "" to run the CLI.
	Server func(context.Context) string
	// Warn receives server failures before falling back to the CLI.
	Warn func(error)
}

type WhisperCPP struct {
	config WhisperCPPConfig
}

var (
	whisperLoadTimePattern  = regexp.MustCompile(`whisper_print_timings:\s+load time =\s+([0-9.]+) ms`)
	whisperTotalTimePattern = regexp.MustCompile(`whisper_print_timings:\s+total time =\s+([0-9.]+) ms`)
)

func NewWhisperCPP(config WhisperCPPConfig) (*WhisperCPP, error) {
	if config.Binary == "" || config.Model == "" || config.VADModel == "" {
		return nil, errors.New("whisper.cpp binary, model, and VAD model are required")
	}
	if _, err := os.Stat(config.Binary); err != nil {
		return nil, fmt.Errorf("whisper.cpp binary: %w", err)
	}
	if _, err := os.Stat(config.Model); err != nil {
		return nil, fmt.Errorf("whisper.cpp model: %w", err)
	}
	if _, err := os.Stat(config.VADModel); err != nil {
		return nil, fmt.Errorf("whisper.cpp VAD model: %w", err)
	}
	if config.Language == "" {
		config.Language = "en"
	}
	if config.Threads < 1 {
		config.Threads = 4
	}
	return &WhisperCPP{config: config}, nil
}

func (w *WhisperCPP) Transcribe(ctx context.Context, request Request) (Result, error) {
	info, err := voxaudio.InspectWAV(request.AudioPath)
	if err != nil {
		return Result{}, err
	}
	prompt, err := whisperPrompt(request.Prompt, request.HotwordsPath)
	if err != nil {
		return Result{}, err
	}
	if w.config.Server != nil {
		if url := w.config.Server(ctx); url != "" {
			result, err := w.transcribeServer(ctx, url, request.AudioPath, prompt, info.Duration)
			if err == nil {
				return result, nil
			}
			if w.config.Warn != nil {
				w.config.Warn(err)
			}
		}
	}

	// whisper.cpp creates its JSON output itself. Keep it inside a private
	// directory so the transcript cannot become world-readable through the
	// process umask on a multi-user machine.
	outputDir, err := os.MkdirTemp("", "vox-whisper-*")
	if err != nil {
		return Result{}, fmt.Errorf("create private whisper output directory: %w", err)
	}
	if err := os.Chmod(outputDir, 0o700); err != nil {
		_ = os.RemoveAll(outputDir)
		return Result{}, fmt.Errorf("protect whisper output directory: %w", err)
	}
	defer os.RemoveAll(outputDir)
	prefix := filepath.Join(outputDir, "transcript")
	jsonPath := prefix + ".json"

	args := []string{
		"-m", w.config.Model,
		"-f", request.AudioPath,
		"-l", w.config.Language,
		"-t", strconv.Itoa(w.config.Threads),
		"-oj",
		"-of", prefix,
		"-nt",
		"--vad",
		"--vad-model", w.config.VADModel,
	}
	if !w.config.UseGPU {
		args = append(args, "-ng")
	}
	if prompt != "" {
		args = append(args, "--prompt", prompt)
	}

	started := time.Now()
	cmd := exec.CommandContext(ctx, w.config.Binary, args...)
	stderr := limitedBuffer{limit: 1024 * 1024}
	cmd.Stdout = io.Discard
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return Result{}, fmt.Errorf("whisper.cpp failed: %w: %s", err, tail(stderr.String(), 1200))
	}
	if stderr.exceeded {
		return Result{}, errors.New("whisper.cpp diagnostic output exceeds 1 MiB")
	}
	latency := time.Since(started)
	output, err := readLimitedFile(jsonPath, 8*1024*1024)
	if err != nil {
		return Result{}, fmt.Errorf("read whisper.cpp JSON: %w", err)
	}
	text, err := parseWhisperJSON(output)
	if err != nil {
		return Result{}, fmt.Errorf("parse whisper.cpp JSON: %w", err)
	}
	loadLatency, totalLatency := parseWhisperTimings(stderr.String())
	inferenceLatency := totalLatency - loadLatency
	if inferenceLatency <= 0 {
		inferenceLatency = latency - loadLatency
	}
	if inferenceLatency <= 0 {
		inferenceLatency = latency
	}

	return Result{
		Text:             text,
		AudioDuration:    info.Duration,
		Latency:          latency,
		ModelLoadLatency: loadLatency,
		InferenceLatency: inferenceLatency,
		RealTimeFactor:   inferenceLatency.Seconds() / info.Duration.Seconds(),
	}, nil
}

// transcribeServer sends the WAV to a warm whisper-server. beam_size matches
// the CLI default (5); the server would otherwise decode greedily.
func (w *WhisperCPP) transcribeServer(ctx context.Context, url, audioPath, prompt string, duration time.Duration) (Result, error) {
	audio, err := os.ReadFile(audioPath)
	if err != nil {
		return Result{}, err
	}
	var body bytes.Buffer
	form := multipart.NewWriter(&body)
	part, err := form.CreateFormFile("file", filepath.Base(audioPath))
	if err != nil {
		return Result{}, err
	}
	_, _ = part.Write(audio)
	for key, value := range map[string]string{
		"prompt": prompt, "language": w.config.Language, "response_format": "json",
		"beam_size": "5", "no_timestamps": "true",
	} {
		_ = form.WriteField(key, value)
	}
	if err := form.Close(); err != nil {
		return Result{}, err
	}
	started := time.Now()
	httpRequest, err := http.NewRequestWithContext(ctx, http.MethodPost, url+"/inference", &body)
	if err != nil {
		return Result{}, err
	}
	httpRequest.Header.Set("Content-Type", form.FormDataContentType())
	response, err := http.DefaultClient.Do(httpRequest)
	if err != nil {
		return Result{}, fmt.Errorf("whisper-server: %w", err)
	}
	defer response.Body.Close()
	data, err := io.ReadAll(io.LimitReader(response.Body, 8*1024*1024))
	if err != nil {
		return Result{}, fmt.Errorf("whisper-server: %w", err)
	}
	var parsed struct {
		Text  string `json:"text"`
		Error string `json:"error"`
	}
	if response.StatusCode != http.StatusOK || json.Unmarshal(data, &parsed) != nil || parsed.Error != "" {
		return Result{}, fmt.Errorf("whisper-server: status %d: %s", response.StatusCode, tail(string(data), 300))
	}
	latency := time.Since(started)
	return Result{
		Text:             strings.TrimSpace(parsed.Text),
		AudioDuration:    duration,
		Latency:          latency,
		InferenceLatency: latency,
		RealTimeFactor:   latency.Seconds() / duration.Seconds(),
	}, nil
}

type limitedBuffer struct {
	buffer   bytes.Buffer
	limit    int
	exceeded bool
}

func (w *limitedBuffer) Write(data []byte) (int, error) {
	written := len(data)
	remaining := w.limit - w.buffer.Len()
	if remaining < len(data) {
		w.exceeded = true
	}
	if remaining > 0 {
		if remaining > len(data) {
			remaining = len(data)
		}
		_, _ = w.buffer.Write(data[:remaining])
	}
	return written, nil
}

func (w *limitedBuffer) String() string {
	return w.buffer.String()
}

func readLimitedFile(path string, maximumBytes int64) ([]byte, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	data, err := io.ReadAll(io.LimitReader(file, maximumBytes+1))
	if err != nil {
		return nil, err
	}
	if int64(len(data)) > maximumBytes {
		return nil, fmt.Errorf("output exceeds %d bytes", maximumBytes)
	}
	return data, nil
}

func parseWhisperJSON(output []byte) (string, error) {
	var result struct {
		Transcription []struct {
			Text string `json:"text"`
		} `json:"transcription"`
	}
	if err := json.Unmarshal(output, &result); err != nil {
		return "", err
	}
	if result.Transcription == nil {
		return "", errors.New("missing transcription array")
	}
	var text strings.Builder
	for _, segment := range result.Transcription {
		text.WriteString(segment.Text)
	}
	return strings.TrimSpace(text.String()), nil
}

func parseWhisperTimings(output string) (time.Duration, time.Duration) {
	return parseMilliseconds(output, whisperLoadTimePattern), parseMilliseconds(output, whisperTotalTimePattern)
}

func parseMilliseconds(output string, pattern *regexp.Regexp) time.Duration {
	match := pattern.FindStringSubmatch(output)
	if len(match) != 2 {
		return 0
	}
	milliseconds, err := strconv.ParseFloat(match[1], 64)
	if err != nil {
		return 0
	}
	return time.Duration(milliseconds * float64(time.Millisecond))
}

func whisperPrompt(base, path string) (string, error) {
	base = strings.Join(strings.Fields(base), " ")
	if path == "" {
		return base, nil
	}
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("context prompt file: %w", err)
	}
	defer file.Close()
	const maximumPromptBytes = 16 * 1024
	data, err := io.ReadAll(io.LimitReader(file, maximumPromptBytes+1))
	if err != nil {
		return "", fmt.Errorf("read context prompt file: %w", err)
	}
	if len(data) > maximumPromptBytes {
		return "", errors.New("context prompt file exceeds 16 KiB")
	}
	var phrases []string
	for _, line := range strings.Split(string(data), "\n") {
		phrase := strings.Join(strings.Fields(line), " ")
		if phrase != "" {
			phrases = append(phrases, phrase)
		}
	}
	if len(phrases) == 0 {
		return base, nil
	}
	return strings.TrimSpace(base + " Vocabulary: " + strings.Join(phrases, ", ") + "."), nil
}

func DefaultWhisperCPPConfig(projectRoot string) WhisperCPPConfig {
	runtimeRoot := filepath.Join(projectRoot, ".local", "runtime", "whisper.cpp-v1.9.1-cuda")
	binary := firstExisting(
		os.Getenv("VOX_WHISPER_BIN"),
		filepath.Join(runtimeRoot, "bin", "whisper-cli"),
	)
	model := os.Getenv("VOX_WHISPER_MODEL")
	if model == "" {
		model = filepath.Join(projectRoot, ".local", "models", "whisper-large-v3-turbo-q8_0", "ggml-large-v3-turbo-q8_0.bin")
	}
	vadModel := os.Getenv("VOX_WHISPER_VAD_MODEL")
	if vadModel == "" {
		vadModel = filepath.Join(projectRoot, ".local", "models", "whisper-vad", "ggml-silero-v6.2.0.bin")
	}
	threads := 8
	if value := os.Getenv("VOX_THREADS"); value != "" {
		if parsed, err := strconv.Atoi(value); err == nil && parsed > 0 {
			threads = parsed
		}
	}
	return WhisperCPPConfig{Binary: binary, Model: model, VADModel: vadModel, Language: "en", Threads: threads, UseGPU: true}
}

func firstExisting(paths ...string) string {
	for _, path := range paths {
		if path == "" {
			continue
		}
		if _, err := os.Stat(path); err == nil {
			return path
		}
	}
	for _, path := range paths {
		if path != "" {
			return path
		}
	}
	return ""
}

func tail(value string, limit int) string {
	if len(value) <= limit {
		return value
	}
	return value[len(value)-limit:]
}
