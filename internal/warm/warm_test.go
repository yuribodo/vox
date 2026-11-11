package warm

import (
	"context"
	"os"
	"testing"
	"time"
)

func TestReadyIgnoresMissingAndDeadSupervisors(t *testing.T) {
	dir := t.TempDir()
	if _, ok := Ready(context.Background(), dir, time.Second); ok {
		t.Fatal("no state must not be ready")
	}
	// PID 2^22+1 is above Linux's pid_max, so it can never be alive.
	if err := writeState(dir, State{PID: 4194305, Ready: true, WhisperURL: "http://x"}); err != nil {
		t.Fatal(err)
	}
	started := time.Now()
	if _, ok := Ready(context.Background(), dir, time.Second); ok || time.Since(started) > 500*time.Millisecond {
		t.Fatal("a dead supervisor must be rejected without waiting")
	}
}

func TestReadyWaitsForLoadingSupervisorAndTouches(t *testing.T) {
	dir := t.TempDir()
	if err := writeState(dir, State{PID: os.Getpid()}); err != nil {
		t.Fatal(err)
	}
	go func() {
		time.Sleep(150 * time.Millisecond)
		_ = writeState(dir, State{PID: os.Getpid(), Ready: true, WhisperURL: "http://127.0.0.1:1/t"})
	}()
	state, ok := Ready(context.Background(), dir, 2*time.Second)
	if !ok || state.WhisperURL != "http://127.0.0.1:1/t" {
		t.Fatalf("state=%+v ok=%v", state, ok)
	}
	if _, err := os.Stat(usedPath(dir)); err != nil {
		t.Fatal("Ready must record use for the idle timer")
	}
	if err := writeState(dir, State{PID: os.Getpid()}); err != nil {
		t.Fatal(err)
	}
	if _, ok := Ready(context.Background(), dir, 0); ok {
		t.Fatal("a loading supervisor with no wait must fall back")
	}
}
