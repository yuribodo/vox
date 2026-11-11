// Package warm keeps the Whisper and polish models loaded between dictations.
// The first recording starts a detached supervisor ("vox warm") that runs
// whisper-server and llama-server while the user speaks, and stops both after
// an idle period so the GPU memory is released. Clients fall back to the
// one-shot binaries whenever the servers are not ready.
package warm

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"syscall"
	"time"
)

type State struct {
	PID        int    `json:"pid"`
	Ready      bool   `json:"ready"`
	WhisperURL string `json:"whisper_url"`
	LLMSocket  string `json:"llm_socket,omitempty"`
}

type Config struct {
	Dir           string
	WhisperServer string
	WhisperModel  string
	VADModel      string
	Language      string
	LlamaServer   string // optional, with LLMModel
	LLMModel      string
	Idle          time.Duration
}

func statePath(dir string) string { return filepath.Join(dir, "warm.json") }
func usedPath(dir string) string  { return filepath.Join(dir, "warm.used") }

// Serve runs the supervisor until the servers are idle for cfg.Idle. It
// returns at once when another supervisor already holds the lock.
func Serve(ctx context.Context, cfg Config) error {
	if err := os.MkdirAll(cfg.Dir, 0o700); err != nil {
		return err
	}
	lock, err := os.OpenFile(filepath.Join(cfg.Dir, "warm.lock"), os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return err
	}
	defer lock.Close()
	if err := syscall.Flock(int(lock.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		return nil
	}

	token := make([]byte, 16)
	if _, err := rand.Read(token); err != nil {
		return err
	}
	port, err := freePort()
	if err != nil {
		return err
	}
	// whisper-server only listens on TCP and has a /load route and permissive
	// CORS, so every route sits behind a secret prefix only Vox can read.
	prefix := "/" + hex.EncodeToString(token)
	public := filepath.Join(cfg.Dir, "warm-public")
	if err := os.MkdirAll(public, 0o700); err != nil {
		return err
	}
	state := State{PID: os.Getpid(), WhisperURL: fmt.Sprintf("http://127.0.0.1:%d%s", port, prefix)}
	logFile, err := os.OpenFile(filepath.Join(cfg.Dir, "warm.log"), os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0o600)
	if err != nil {
		return err
	}
	defer logFile.Close()

	var children []*exec.Cmd
	defer func() {
		for _, child := range children {
			_ = child.Process.Signal(syscall.SIGTERM)
		}
		for _, child := range children {
			_ = child.Wait()
		}
		_ = os.Remove(statePath(cfg.Dir))
		_ = os.RemoveAll(public)
		if state.LLMSocket != "" {
			_ = os.Remove(state.LLMSocket)
		}
	}()
	exited := make(chan error, 2)
	start := func(binary string, args ...string) error {
		cmd := exec.Command(binary, args...)
		cmd.Stderr = logFile // stdout may echo transcripts; never keep it
		if err := cmd.Start(); err != nil {
			return err
		}
		children = append(children, cmd)
		go func() { exited <- cmd.Wait() }()
		return nil
	}
	if err := start(cfg.WhisperServer, "-m", cfg.WhisperModel, "--vad", "-vm", cfg.VADModel, "-l", cfg.Language,
		"--host", "127.0.0.1", "--port", strconv.Itoa(port), "--request-path", prefix, "--public", public); err != nil {
		return fmt.Errorf("start whisper-server: %w", err)
	}
	if cfg.LlamaServer != "" && cfg.LLMModel != "" {
		state.LLMSocket = filepath.Join(cfg.Dir, "llm.sock")
		_ = os.Remove(state.LLMSocket)
		// Same VRAM-safe sizing as the one-shot polish; a Unix socket keeps it private.
		if err := start(cfg.LlamaServer, "-m", cfg.LLMModel, "--host", state.LLMSocket, "--port", "1",
			"-fitt", "256", "-c", "2048", "-b", "512", "-ub", "256", "-np", "1", "--no-webui"); err != nil {
			return fmt.Errorf("start llama-server: %w", err)
		}
	}
	if err := writeState(cfg.Dir, state); err != nil {
		return err
	}
	if err := waitHealthy(ctx, state, exited); err != nil {
		return err
	}
	state.Ready = true
	if err := writeState(cfg.Dir, state); err != nil {
		return err
	}
	Touch(cfg.Dir)

	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case err := <-exited:
			return fmt.Errorf("warm server exited: %v", err)
		case <-ticker.C:
			info, err := os.Stat(usedPath(cfg.Dir))
			if err != nil || time.Since(info.ModTime()) > cfg.Idle {
				return nil
			}
		}
	}
}

func waitHealthy(ctx context.Context, state State, exited <-chan error) error {
	ctx, cancel := context.WithTimeout(ctx, 90*time.Second)
	defer cancel()
	for {
		if healthy(ctx, http.DefaultClient, state.WhisperURL+"/health") &&
			(state.LLMSocket == "" || healthy(ctx, UnixClient(state.LLMSocket), "http://unix/health")) {
			return nil
		}
		select {
		case <-ctx.Done():
			return errors.New("warm servers did not become ready")
		case err := <-exited:
			return fmt.Errorf("warm server exited while loading: %v", err)
		case <-time.After(200 * time.Millisecond):
		}
	}
}

func healthy(ctx context.Context, client *http.Client, url string) bool {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return false
	}
	response, err := client.Do(request)
	if err != nil {
		return false
	}
	response.Body.Close()
	return response.StatusCode == http.StatusOK
}

// UnixClient sends HTTP requests to a Unix socket; URLs use the host "unix".
func UnixClient(socket string) *http.Client {
	return &http.Client{Transport: &http.Transport{
		DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			return (&net.Dialer{}).DialContext(ctx, "unix", socket)
		},
	}}
}

func freePort() (int, error) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return 0, err
	}
	defer listener.Close()
	return listener.Addr().(*net.TCPAddr).Port, nil
}

func writeState(dir string, state State) error {
	data, err := json.Marshal(state)
	if err != nil {
		return err
	}
	temporary := statePath(dir) + ".tmp"
	if err := os.WriteFile(temporary, data, 0o600); err != nil {
		return err
	}
	return os.Rename(temporary, statePath(dir))
}

// Touch records use so the supervisor's idle timer restarts.
func Touch(dir string) {
	now := time.Now()
	if err := os.Chtimes(usedPath(dir), now, now); errors.Is(err, os.ErrNotExist) {
		_ = os.WriteFile(usedPath(dir), nil, 0o600)
	}
}

// read returns the state of a live supervisor.
func read(dir string) (State, bool) {
	data, err := os.ReadFile(statePath(dir))
	if err != nil {
		return State{}, false
	}
	var state State
	if json.Unmarshal(data, &state) != nil || state.PID <= 0 || syscall.Kill(state.PID, 0) != nil {
		return State{}, false
	}
	return state, true
}

// Start launches a detached supervisor unless one is already running.
func Start(dir, executable string) error {
	Touch(dir)
	if _, ok := read(dir); ok {
		return nil
	}
	cmd := exec.Command(executable, "warm")
	cmd.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
	if err := cmd.Start(); err != nil {
		return err
	}
	return cmd.Process.Release()
}

// Ready waits up to wait for a loading supervisor and returns its state.
func Ready(ctx context.Context, dir string, wait time.Duration) (State, bool) {
	deadline := time.Now().Add(wait)
	for {
		state, ok := read(dir)
		if ok && state.Ready {
			Touch(dir)
			return state, true
		}
		if !ok || time.Now().After(deadline) {
			return State{}, false
		}
		select {
		case <-ctx.Done():
			return State{}, false
		case <-time.After(100 * time.Millisecond):
		}
	}
}
