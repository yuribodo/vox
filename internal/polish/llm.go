package polish

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// S1-mini by Superwhisper is trained on this exact system prompt and control
// line; its model card warns that other wording makes it hallucinate.
const (
	systemPrompt = "You are a text normalizer for speech-to-text transcripts. The input begins " +
		"with a control line specifying the styling, structure, and context settings; " +
		"clean the transcript to match those settings and output only the cleaned text."
	controlLine = "[Styling: semi-formal] [Structure: prose] [Context: general]"
)

// Cleaning mostly deletes (fillers, abandoned self-corrections) and fixes a
// few words. A model that answers or rewrites the text invents many words, and
// one that summarizes drops most of them; both are rejected.
const (
	maxNovel = 0.35 // share of output words absent from the transcript
	minKept  = 0.4  // output length relative to the transcript
)

// guard returns why polished is not a faithful cleanup of text, or "".
func guard(text, polished string) string {
	in, out := words(text), words(polished)
	if len(out) < int(minKept*float64(len(in))) {
		return fmt.Sprintf("model dropped %d of %d words", len(in)-len(out), len(in))
	}
	seen := map[string]int{}
	for _, word := range in {
		seen[word]++
	}
	novel := 0
	for _, word := range out {
		if seen[word] > 0 {
			seen[word]--
		} else {
			novel++
		}
	}
	// Two fixed words are always fine: short dictations have little to compare.
	if novel > 2 && float64(novel) > maxNovel*float64(len(out)) {
		return fmt.Sprintf("model invented %d of %d words", novel, len(out))
	}
	return ""
}

// LLM runs a one-shot llama.cpp completion to polish a transcript.
type LLM struct {
	Binary  string
	Model   string
	Timeout time.Duration
	// Server returns a ready llama-server HTTP client, or nil to run the CLI.
	Server func(context.Context) *http.Client
}

// DefaultLLM returns the pinned runtime from scripts/fetch-llm.sh, or nil when
// it is not installed or VOX_POLISH=0.
func DefaultLLM(projectRoot string) *LLM {
	if os.Getenv("VOX_POLISH") == "0" {
		return nil
	}
	binary := os.Getenv("VOX_LLM_BIN")
	if binary == "" {
		binary = filepath.Join(projectRoot, ".local", "runtime", "llama.cpp-b11912-cuda", "bin", "llama-completion")
	}
	model := os.Getenv("VOX_LLM_MODEL")
	if model == "" {
		// Prefer the developer fine-tune from scripts/finetune/run.sh.
		model = filepath.Join(projectRoot, ".local", "models", "s1-mini-vox-q4_k_m", "s1-mini-vox-q4_k_m.gguf")
		if _, err := os.Stat(model); err != nil {
			model = filepath.Join(projectRoot, ".local", "models", "s1-mini-q4_k_m", "s1-mini-q4_k_m.gguf")
		}
	}
	for _, path := range []string{binary, model} {
		if _, err := os.Stat(path); err != nil {
			return nil
		}
	}
	return &LLM{Binary: binary, Model: model, Timeout: 10 * time.Second}
}

func (l LLM) Polish(ctx context.Context, text string) (string, error) {
	ctx, cancel := context.WithTimeout(ctx, l.Timeout)
	defer cancel()
	words := len(strings.Fields(text))
	output, err := l.complete(ctx, text, 2*words+64)
	if err != nil {
		return "", err
	}
	polished := strings.TrimSpace(strings.TrimSuffix(strings.TrimSpace(output), "[end of text]"))
	if polished == "" {
		return "", errors.New("polish: model returned nothing")
	}
	if reason := guard(text, polished); reason != "" {
		return "", fmt.Errorf("polish: rejected, %s", reason)
	}
	return polished, nil
}

// complete asks a warm llama-server, falling back to a one-shot process.
func (l LLM) complete(ctx context.Context, text string, limit int) (string, error) {
	if l.Server != nil {
		if client := l.Server(ctx); client != nil {
			output, err := serverComplete(ctx, client, chatPrompt(text), limit)
			if err == nil {
				return output, nil
			}
		}
	}
	cmd := exec.CommandContext(ctx, l.Binary,
		"-m", l.Model,
		"-no-cnv", "--no-display-prompt", "--simple-io", "--no-warmup",
		// Small context and batches for a 4 GiB GPU; without -ngl, llama.cpp fits
		// as many layers as free VRAM allows instead of failing.
		"-fitt", "256", "-c", "2048", "-b", "512", "-ub", "256", "--temp", "0",
		"-n", strconv.Itoa(limit),
		"-p", chatPrompt(text),
	)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("polish: llama.cpp failed: %w: %s", err, tail(stderr.String(), 600))
	}
	return stdout.String(), nil
}

func serverComplete(ctx context.Context, client *http.Client, prompt string, limit int) (string, error) {
	payload, err := json.Marshal(map[string]any{"prompt": prompt, "n_predict": limit, "temperature": 0, "cache_prompt": true})
	if err != nil {
		return "", err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, "http://unix/completion", bytes.NewReader(payload))
	if err != nil {
		return "", err
	}
	request.Header.Set("Content-Type", "application/json")
	response, err := client.Do(request)
	if err != nil {
		return "", err
	}
	defer response.Body.Close()
	var parsed struct {
		Content string `json:"content"`
	}
	if err := json.NewDecoder(io.LimitReader(response.Body, 4*1024*1024)).Decode(&parsed); err != nil {
		return "", err
	}
	if response.StatusCode != http.StatusOK {
		return "", fmt.Errorf("llama-server: status %d", response.StatusCode)
	}
	return parsed.Content, nil
}

// chatPrompt builds the ChatML by hand so -no-cnv runs exactly one turn. The
// empty think block is the assistant prefix S1-mini was trained with.
func chatPrompt(text string) string {
	return "<|im_start|>system\n" + systemPrompt + "<|im_end|>\n" +
		"<|im_start|>user\n" + controlLine + "\n" + strings.ReplaceAll(text, "<|", "< |") + "<|im_end|>\n" +
		"<|im_start|>assistant\n<think>\n\n</think>\n\n"
}

func tail(value string, limit int) string {
	if len(value) <= limit {
		return value
	}
	return value[len(value)-limit:]
}
