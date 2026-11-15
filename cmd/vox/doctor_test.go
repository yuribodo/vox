package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func TestWriteDoctorReport(t *testing.T) {
	for _, tt := range []struct {
		name      string
		checks    []doctorCheck
		wantError bool
	}{
		{"healthy", []doctorCheck{{Name: "pw-record", Status: "ok", Required: true}, {Name: "CUDA user-space libraries", Status: "available", Required: true}}, false},
		{"optional tmux missing", []doctorCheck{{Name: "tmux", Status: "not installed", Required: false}}, false},
		{"required tool missing", []doctorCheck{{Name: "pw-record", Status: "not installed", Required: true}}, true},
		{"runtime unavailable", []doctorCheck{{Name: "whisper runtime/model", Status: "unavailable", Required: true}}, true},
		{"CUDA advisory", []doctorCheck{{Name: "CUDA user-space libraries", Status: "missing libcudnn.so.9", Required: false}}, false},
		{"CUDA unknown", []doctorCheck{{Name: "CUDA user-space libraries", Status: "unknown (ldconfig unavailable)", Required: false}}, false},
	} {
		t.Run(tt.name, func(t *testing.T) {
			var out bytes.Buffer
			err := writeDoctorReport(&out, tt.checks)
			if (err != nil) != tt.wantError {
				t.Fatalf("error = %v", err)
			}
			var decoded []map[string]any
			if err := json.Unmarshal(out.Bytes(), &decoded); err != nil {
				t.Fatalf("invalid report: %v", err)
			}
			if len(decoded) != len(tt.checks) {
				t.Fatal("checks lost")
			}
			for i, c := range tt.checks {
				if decoded[i]["name"] != c.Name || decoded[i]["status"] != c.Status || decoded[i]["required"] != c.Required {
					t.Fatalf("unexpected schema: %v", decoded[i])
				}
			}
			if tt.wantError && !strings.Contains(err.Error(), tt.checks[0].Name) {
				t.Fatalf("missing failing check name: %v", err)
			}
		})
	}
}

type failingDoctorWriter struct{}

func (failingDoctorWriter) Write([]byte) (int, error) { return 0, io.ErrClosedPipe }
func TestWriteDoctorReportWriterFailure(t *testing.T) {
	err := writeDoctorReport(failingDoctorWriter{}, []doctorCheck{{Name: "pw-record", Status: "not installed", Required: true}})
	if !errors.Is(err, io.ErrClosedPipe) {
		t.Fatalf("error = %v", err)
	}
}

// Exercise the actual executable contract, including stdout JSON and exit status,
// without requiring audio, a GPU, or the host's installed tools.
func TestDoctorExecutable(t *testing.T) {
	root := t.TempDir()
	binary := filepath.Join(root, "vox")
	build := exec.Command("go", "build", "-buildvcs=false", "-o", binary, ".")
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build: %v: %s", err, output)
	}
	if err := os.WriteFile(filepath.Join(root, "go.mod"), []byte("module test"), 0600); err != nil {
		t.Fatal(err)
	}
	fixture := filepath.Join(root, "fixture")
	if err := os.WriteFile(fixture, []byte("fixture"), 0600); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		name          string
		tools         bool
		wantFailure   bool
		cudaScript    string
		cudaStatus    string
		driverFailure bool
	}{
		{"missing required tools", false, true, "", "unknown (ldconfig unavailable)", false},
		{"optional tools absent", true, false, "", "unknown (ldconfig unavailable)", false},
		{"CUDA cached", true, false, "echo libcublasLt.so.13 libcudnn.so.9", "available", false},
		{"CUDA cache missing cublas", true, false, "echo libcudnn.so.9", "missing libcublasLt.so.13", false},
		{"CUDA cache missing cudnn", true, false, "echo libcublasLt.so.13", "missing libcudnn.so.9", false},
		{"CUDA cache command fails", true, false, "exit 1", "unknown (ldconfig unavailable)", false},
		{"driver command fails", true, true, "", "unknown (ldconfig unavailable)", true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			bin := t.TempDir()
			if tc.tools {
				for _, name := range []string{"pw-record", "pw-dump", "wpctl", "nvidia-smi"} {
					if err := os.WriteFile(filepath.Join(bin, name), []byte("#!/bin/sh\nexit 0\n"), 0700); err != nil {
						t.Fatal(err)
					}
				}
			}
			if tc.cudaScript != "" {
				if err := os.WriteFile(filepath.Join(bin, "ldconfig"), []byte("#!/bin/sh\n"+tc.cudaScript+"\n"), 0700); err != nil {
					t.Fatal(err)
				}
			}
			if tc.driverFailure {
				if err := os.WriteFile(filepath.Join(bin, "nvidia-smi"), []byte("#!/bin/sh\necho unavailable\nexit 1\n"), 0700); err != nil {
					t.Fatal(err)
				}
			}
			cmd := exec.Command(binary, "doctor")
			cmd.Env = []string{"PATH=" + bin, "VOX_WHISPER_BIN=" + fixture, "VOX_WHISPER_MODEL=" + fixture, "VOX_WHISPER_VAD_MODEL=" + fixture}
			var stdout, stderr bytes.Buffer
			cmd.Stdout = &stdout
			cmd.Stderr = &stderr
			err := cmd.Run()
			if (err != nil) != tc.wantFailure {
				t.Fatalf("exit: %v; stderr: %s", err, stderr.String())
			}
			var checks []doctorCheck
			if err := json.Unmarshal(stdout.Bytes(), &checks); err != nil {
				t.Fatalf("JSON: %v: %s", err, stdout.String())
			}
			if len(checks) != 7 {
				t.Fatalf("incomplete report: %v", checks)
			}
			if tc.wantFailure && !strings.Contains(stderr.String(), "required checks failed") {
				t.Fatalf("missing diagnostic: %s", stderr.String())
			}
			for _, check := range checks {
				if check.Required && check.Status != "ok" && check.Detail == "" {
					t.Fatalf("required failure lacks guidance: %+v", check)
				}
				if tc.driverFailure && check.Name == "NVIDIA driver" && check.Status != "unavailable" {
					t.Fatalf("driver failure: %+v", check)
				}
				if check.Name == "tmux" && (check.Required || check.Status != "not installed") {
					t.Fatalf("tmux must be optional: %+v", check)
				}
				if check.Name == "CUDA user-space libraries" && (check.Required || check.Status != tc.cudaStatus) {
					t.Fatalf("CUDA cache must be advisory: %+v", check)
				}
			}
		})
	}
}
