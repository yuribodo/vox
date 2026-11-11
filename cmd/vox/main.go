package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/yuribodo/vox/internal/asr"
	"github.com/yuribodo/vox/internal/benchmark"
	"github.com/yuribodo/vox/internal/polish"
	"github.com/yuribodo/vox/internal/record"
	voxtmux "github.com/yuribodo/vox/internal/tmux"
	"github.com/yuribodo/vox/internal/toggle"
	"github.com/yuribodo/vox/internal/warm"
)

const version = "0.1.0"

const usage = `vox: private local push-to-talk dictation

Usage:
  vox version
  vox doctor
  vox record --output <path> [--source <pipewire-node>]
  vox transcribe [--hotwords <path>] <audio-path>
  vox benchmark --manifest <path> [--report <path>]
  vox insert --target <tmux-pane> [--text <text> | --stdin]
  vox toggle (--target <tmux-pane> | --output <path>) [--source <pipewire-node>]
  vox cancel

Safety: insert and toggle paste text but never submit it.`

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	if err := run(ctx, os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, "vox:", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, args []string) error {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, usage)
		return errors.New("a command is required")
	}
	switch args[0] {
	case "version", "--version":
		fmt.Println("vox", version)
		return nil
	case "help", "--help", "-h":
		fmt.Println(usage)
		return nil
	}
	root, err := projectRoot()
	if err != nil {
		return err
	}
	switch args[0] {
	case "doctor":
		return doctor(root)
	case "record":
		return recordCommand(ctx, args[1:])
	case "transcribe":
		return transcribeCommand(ctx, root, args[1:])
	case "benchmark":
		return benchmarkCommand(ctx, root, args[1:])
	case "insert":
		return insertCommand(ctx, args[1:])
	case "toggle":
		return toggleCommand(ctx, root, args[1:])
	case "cancel":
		return cancelCommand(ctx, args[1:])
	case "warm":
		return warmCommand(ctx, root)
	default:
		return fmt.Errorf("unknown command %q", args[0])
	}
}

func doctor(root string) error {
	type check struct {
		Name   string `json:"name"`
		Status string `json:"status"`
		Detail string `json:"detail,omitempty"`
	}
	checks := []check{}
	for _, name := range []string{"pw-record", "pw-dump", "wpctl", "tmux"} {
		_, err := exec.LookPath(name)
		status := "ok"
		if err != nil {
			status = "not installed"
		}
		checks = append(checks, check{Name: name, Status: status})
	}
	if _, err := exec.LookPath("nvidia-smi"); err != nil {
		checks = append(checks, check{Name: "NVIDIA driver", Status: "not installed"})
	} else {
		output, runErr := exec.Command("nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader").CombinedOutput()
		if runErr != nil {
			checks = append(checks, check{Name: "NVIDIA driver", Status: "unavailable", Detail: strings.TrimSpace(string(output))})
		} else {
			checks = append(checks, check{Name: "NVIDIA driver", Status: "ok", Detail: strings.TrimSpace(string(output))})
		}
	}
	if _, err := asr.NewWhisperCPP(asr.DefaultWhisperCPPConfig(root)); err != nil {
		checks = append(checks, check{Name: "whisper runtime/model", Status: "unavailable", Detail: err.Error()})
	} else {
		checks = append(checks, check{Name: "whisper runtime/model", Status: "ok", Detail: "provider=cuda"})
	}
	checks = append(checks, check{Name: "CUDA user-space libraries", Status: cudaLibraryStatus()})
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	return encoder.Encode(checks)
}

func cudaLibraryStatus() string {
	output, err := exec.Command("ldconfig", "-p").Output()
	if err != nil || !strings.Contains(string(output), "libcublasLt.so.13") {
		return "missing libcublasLt.so.13"
	}
	if !strings.Contains(string(output), "libcudnn.so.9") {
		return "missing libcudnn.so.9"
	}
	return "available"
}

func recordCommand(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("record", flag.ContinueOnError)
	output := flags.String("output", "", "output WAV path")
	source := flags.String("source", "", "PipeWire source node")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *output == "" {
		return errors.New("record requires --output")
	}
	fmt.Fprintln(os.Stderr, "Recording… press Ctrl-C to stop.")
	err := (record.Recorder{Binary: "pw-record", Target: *source}).Record(ctx, *output)
	if err == nil {
		fmt.Fprintln(os.Stderr, "Recording saved.")
	}
	return err
}

func transcribeCommand(ctx context.Context, root string, args []string) error {
	flags := flag.NewFlagSet("transcribe", flag.ContinueOnError)
	hotwords := flags.String("hotwords", "", "one hotword phrase per line")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() != 1 {
		return errors.New("transcribe requires exactly one audio path")
	}
	transcriber, err := newTranscriber(root)
	if err != nil {
		return err
	}
	fmt.Fprintln(os.Stderr, "Processing…")
	result, err := transcriber.Transcribe(ctx, asr.Request{AudioPath: flags.Arg(0), HotwordsPath: *hotwords})
	if err != nil {
		return err
	}
	fmt.Println(result.Text)
	fmt.Fprintf(os.Stderr, "Cold wall %.0f ms; model load %.0f ms; inference %.0f ms; RTF %.3f\n",
		float64(result.Latency.Microseconds())/1000,
		float64(result.ModelLoadLatency.Microseconds())/1000,
		float64(result.InferenceLatency.Microseconds())/1000,
		result.RealTimeFactor)
	return nil
}

func benchmarkCommand(ctx context.Context, root string, args []string) error {
	flags := flag.NewFlagSet("benchmark", flag.ContinueOnError)
	manifestPath := flags.String("manifest", "", "benchmark manifest")
	reportPath := flags.String("report", "", "Markdown report")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *manifestPath == "" {
		return errors.New("benchmark requires --manifest")
	}
	manifest, err := benchmark.LoadManifest(*manifestPath)
	if err != nil {
		return err
	}
	transcriber, err := asr.NewWhisperCPP(asr.DefaultWhisperCPPConfig(root))
	if err != nil {
		return err
	}
	polished, err := newTranscriber(root)
	if err != nil {
		return err
	}
	report := benchmark.Run(ctx, transcriber, polished, manifest)
	outputPath := *reportPath
	if outputPath == "" {
		outputPath = filepath.Join(root, "artifacts", "whisper-benchmark-report.md")
	}
	if err := os.MkdirAll(filepath.Dir(outputPath), 0o755); err != nil {
		return err
	}
	if err := os.WriteFile(outputPath, []byte(report.Markdown()), 0o644); err != nil {
		return err
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(report); err != nil {
		return err
	}
	fmt.Fprintln(os.Stderr, "Report written to", outputPath)
	return nil
}

func insertCommand(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("insert", flag.ContinueOnError)
	target := flags.String("target", "", "explicit tmux pane, e.g. %3")
	text := flags.String("text", "", "literal text to insert")
	stdin := flags.Bool("stdin", false, "read exact text from stdin")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *target == "" {
		return errors.New("insert requires --target")
	}
	if (*text == "") == !*stdin {
		return errors.New("choose exactly one of --text or --stdin")
	}
	value := *text
	if *stdin {
		const maximumInsertBytes = 1024 * 1024
		data, err := io.ReadAll(io.LimitReader(os.Stdin, maximumInsertBytes+1))
		if err != nil {
			return err
		}
		if len(data) > maximumInsertBytes {
			return errors.New("stdin exceeds the 1 MiB insertion limit")
		}
		value = string(data)
	}
	return (voxtmux.Inserter{}).Insert(ctx, *target, value)
}

func toggleCommand(ctx context.Context, root string, args []string) error {
	flags := flag.NewFlagSet("toggle", flag.ContinueOnError)
	target := flags.String("target", "", "explicit tmux pane")
	output := flags.String("output", "", "write exact transcript to a new file")
	source := flags.String("source", "", "explicit PipeWire source node for a new recording")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if (*target == "") == (*output == "") {
		return errors.New("toggle requires exactly one of --target or --output")
	}
	transcriber, err := newTranscriber(root)
	if err != nil {
		return err
	}
	toggler := toggle.Toggle{Recorder: record.Recorder{Binary: "pw-record", Target: *source}, Transcriber: transcriber}
	var state string
	if *target != "" {
		state, err = toggler.Run(ctx, *target)
	} else {
		state, err = toggler.RunToFile(ctx, *output)
	}
	if err != nil {
		return err
	}
	if state == "recording" {
		fmt.Fprintln(os.Stderr, "Recording… invoke toggle again to stop.")
		// Load the models while the user speaks.
		if executable, err := os.Executable(); err == nil && os.Getenv("VOX_WARM") != "0" {
			if err := warm.Start(toggle.DefaultStateDir(), executable); err != nil {
				fmt.Fprintln(os.Stderr, "vox: warm servers:", err)
			}
		}
	}
	if state == "inserted" {
		fmt.Fprintln(os.Stderr, "Transcription inserted without submitting.")
	}
	if state == "written" {
		fmt.Fprintln(os.Stderr, "Transcription written without submitting.")
	}
	return nil
}

func cancelCommand(ctx context.Context, args []string) error {
	flags := flag.NewFlagSet("cancel", flag.ContinueOnError)
	if err := flags.Parse(args); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return errors.New("cancel does not accept positional arguments")
	}
	if err := (toggle.Toggle{}).Cancel(ctx); err != nil {
		return err
	}
	fmt.Fprintln(os.Stderr, "Recording cancelled without transcription.")
	return nil
}

// newTranscriber is Whisper plus the developer prompt, user vocabulary and
// replacements, and the local LLM polish when its runtime is installed.
func newTranscriber(root string) (asr.Transcriber, error) {
	warn := func(err error) { fmt.Fprintf(os.Stderr, "vox: %v; falling back\n", err) }
	dir := toggle.DefaultStateDir()
	whisperConfig := asr.DefaultWhisperCPPConfig(root)
	whisperConfig.Warn = warn
	whisperConfig.Server = func(ctx context.Context) string {
		// A short recording can stop before the servers finish loading. Wait
		// rather than fall back: the CLI cannot fit beside them in 4 GiB VRAM.
		state, _ := warm.Ready(ctx, dir, 30*time.Second)
		return state.WhisperURL
	}
	whisper, err := asr.NewWhisperCPP(whisperConfig)
	if err != nil {
		return nil, err
	}
	llm := polish.DefaultLLM(root)
	if llm != nil {
		llm.Server = func(ctx context.Context) *http.Client {
			if state, ok := warm.Ready(ctx, dir, 0); ok && state.LLMSocket != "" {
				return warm.UnixClient(state.LLMSocket)
			}
			return nil
		}
	}
	config := polish.ConfigDir()
	rules, err := polish.LoadRules(filepath.Join(config, "replacements.txt"))
	if err != nil {
		return nil, err
	}
	return polish.Transcriber{
		Inner:          whisper,
		VocabularyPath: filepath.Join(config, "vocabulary.txt"),
		Rules:          slices.Concat(polish.DefaultRules, rules),
		LLM:            llm,
		Warn:           func(err error) { fmt.Fprintf(os.Stderr, "vox: %v; using the Whisper text\n", err) },
	}, nil
}

// warmCommand is the detached supervisor started by the first recording.
func warmCommand(ctx context.Context, root string) error {
	whisper := asr.DefaultWhisperCPPConfig(root)
	config := warm.Config{
		Dir:           toggle.DefaultStateDir(),
		WhisperServer: filepath.Join(filepath.Dir(whisper.Binary), "whisper-server"),
		WhisperModel:  whisper.Model,
		VADModel:      whisper.VADModel,
		Language:      whisper.Language,
		Idle:          10 * time.Minute,
	}
	if minutes, err := strconv.Atoi(os.Getenv("VOX_WARM_IDLE")); err == nil && minutes > 0 {
		config.Idle = time.Duration(minutes) * time.Minute
	}
	if llm := polish.DefaultLLM(root); llm != nil {
		server := filepath.Join(filepath.Dir(llm.Binary), "llama-server")
		if _, err := os.Stat(server); err == nil {
			config.LlamaServer, config.LLMModel = server, llm.Model
		}
	}
	return warm.Serve(ctx, config)
}

func projectRoot() (string, error) {
	executable, err := os.Executable()
	if err != nil {
		return "", err
	}
	executable, err = filepath.EvalSymlinks(executable)
	if err != nil {
		return "", fmt.Errorf("resolve Vox executable: %w", err)
	}
	dir := filepath.Dir(executable)
	if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
		return dir, nil
	}
	return "", fmt.Errorf("cannot find go.mod beside Vox executable in %s; build and run Vox from its repository", strings.TrimSpace(dir))
}
