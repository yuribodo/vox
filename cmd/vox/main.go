package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"

	"github.com/yuribodo/vox/internal/asr"
	"github.com/yuribodo/vox/internal/benchmark"
	"github.com/yuribodo/vox/internal/record"
	voxtmux "github.com/yuribodo/vox/internal/tmux"
	"github.com/yuribodo/vox/internal/toggle"
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
	default:
		return fmt.Errorf("unknown command %q", args[0])
	}
}

type doctorCheck struct {
	Name     string `json:"name"`
	Status   string `json:"status"`
	Detail   string `json:"detail,omitempty"`
	Required bool   `json:"required"`
}

// writeDoctorReport preserves the JSON report even when a required check fails.
func writeDoctorReport(w io.Writer, checks []doctorCheck) error {
	encoder := json.NewEncoder(w)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(checks); err != nil {
		return err
	}
	var failed []string
	for _, check := range checks {
		if check.Required && check.Status != "ok" && check.Status != "available" {
			failed = append(failed, check.Name)
		}
	}
	if len(failed) > 0 {
		return fmt.Errorf("required checks failed: %s; resolve the report details before dictating", strings.Join(failed, ", "))
	}
	return nil
}

const nvidiaDriverCheckName = "NVIDIA driver"

func doctor(root string) error {
	checks := []doctorCheck{}
	for _, name := range []string{"pw-record", "pw-dump", "wpctl", "tmux"} {
		_, err := exec.LookPath(name)
		check := doctorCheck{Name: name, Status: "ok", Required: name != "tmux"}
		if err != nil {
			check.Status = "not installed"
			switch name {
			case "pw-record", "pw-dump":
				check.Detail = "Install PipeWire command-line tools; see README Requirements."
			case "wpctl":
				check.Detail = "Install WirePlumber command-line tools; see README Requirements."
			case "tmux":
				check.Detail = "Optional for desktop dictation; install tmux for terminal-target insertion commands."
			}
		}
		checks = append(checks, check)
	}
	if _, err := exec.LookPath("nvidia-smi"); err != nil {
		checks = append(checks, doctorCheck{Name: nvidiaDriverCheckName, Status: "not installed", Required: true, Detail: "Install the NVIDIA driver for the supported GPU; see README Requirements."})
	} else {
		output, runErr := exec.Command("nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader").CombinedOutput()
		if runErr != nil {
			checks = append(checks, doctorCheck{Name: nvidiaDriverCheckName, Status: "unavailable", Required: true, Detail: "Check the NVIDIA driver installation: " + strings.TrimSpace(string(output))})
		} else {
			checks = append(checks, doctorCheck{Name: nvidiaDriverCheckName, Status: "ok", Required: true, Detail: strings.TrimSpace(string(output))})
		}
	}
	if _, err := asr.NewWhisperCPP(asr.DefaultWhisperCPPConfig(root)); err != nil {
		checks = append(checks, doctorCheck{Name: "whisper runtime/model", Status: "unavailable", Required: true, Detail: err.Error() + "; run make fetch-whisper after installing its prerequisites."})
	} else {
		checks = append(checks, doctorCheck{Name: "whisper runtime/model", Status: "ok", Required: true, Detail: "provider=cuda"})
	}
	cuda := doctorCheck{Name: "CUDA user-space libraries", Status: cudaLibraryStatus(), Required: false}
	if cuda.Status != "available" {
		cuda.Detail = "Advisory loader-cache check only: libraries may be available through runtime search paths. Verify GPU inference and see README Requirements."
	}
	checks = append(checks, cuda)
	return writeDoctorReport(os.Stdout, checks)
}

func cudaLibraryStatus() string {
	output, err := exec.Command("ldconfig", "-p").Output()
	if err != nil {
		return "unknown (ldconfig unavailable)"
	}
	if !strings.Contains(string(output), "libcublasLt.so.13") {
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
	transcriber, err := asr.NewWhisperCPP(asr.DefaultWhisperCPPConfig(root))
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
	report := benchmark.Run(ctx, transcriber, manifest)
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
	transcriber, err := asr.NewWhisperCPP(asr.DefaultWhisperCPPConfig(root))
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
