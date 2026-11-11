package asr

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestParseWhisperJSONJoinsSegments(t *testing.T) {
	output := []byte(`{"transcription":[{"text":" First line."},{"text":" Second line."}]}`)
	got, err := parseWhisperJSON(output)
	if err != nil {
		t.Fatal(err)
	}
	if got != "First line. Second line." {
		t.Fatalf("got %q", got)
	}
}

func TestParseWhisperJSONAcceptsEmptyTranscription(t *testing.T) {
	got, err := parseWhisperJSON([]byte(`{"transcription":[]}`))
	if err != nil {
		t.Fatal(err)
	}
	if got != "" {
		t.Fatalf("got %q", got)
	}
}

func TestParseWhisperJSONRejectsMissingTranscription(t *testing.T) {
	if _, err := parseWhisperJSON([]byte(`{"result":{"language":"en"}}`)); err == nil {
		t.Fatal("expected error")
	}
}

func TestParseWhisperTimings(t *testing.T) {
	output := "whisper_print_timings:     load time =   284.12 ms\n" +
		"whisper_print_timings:    total time =   690.04 ms\n"
	load, total := parseWhisperTimings(output)
	if load != 284120*time.Microsecond || total != 690040*time.Microsecond {
		t.Fatalf("load=%s total=%s", load, total)
	}
}

func TestWhisperPromptNormalizesWhitespaceAndEnforcesLimit(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "prompt.txt")
	if err := os.WriteFile(path, []byte("React Hook Form\nZod\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	got, err := whisperPrompt("", path)
	if err != nil {
		t.Fatal(err)
	}
	if got != "Vocabulary: React Hook Form, Zod." {
		t.Fatalf("got %q", got)
	}
	got, err = whisperPrompt("Fix the  code.", path)
	if err != nil || got != "Fix the code. Vocabulary: React Hook Form, Zod." {
		t.Fatalf("got %q, %v", got, err)
	}

	tooLarge := filepath.Join(dir, "too-large.txt")
	if err := os.WriteFile(tooLarge, make([]byte, 16*1024+1), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := whisperPrompt("", tooLarge); err == nil {
		t.Fatal("expected size error")
	}
}

func TestLimitedBufferCapsDiagnosticOutput(t *testing.T) {
	buffer := limitedBuffer{limit: 4}
	data := []byte("abcdef")
	written, err := buffer.Write(data)
	if err != nil || written != len(data) {
		t.Fatalf("write returned %d, %v", written, err)
	}
	if got := buffer.String(); got != "abcd" || !buffer.exceeded {
		t.Fatalf("buffer=%q exceeded=%v", got, buffer.exceeded)
	}
}
