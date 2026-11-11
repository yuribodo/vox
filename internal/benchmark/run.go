package benchmark

import (
	"context"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/yuribodo/vox/internal/asr"
)

type ModeResult struct {
	Mode             string  `json:"mode"`
	Transcript       string  `json:"transcript"`
	Error            string  `json:"error,omitempty"`
	WER              float64 `json:"wer"`
	WordEdits        int     `json:"word_edits"`
	ReferenceWords   int     `json:"reference_words"`
	TermRecall       Recall  `json:"term_recall"`
	IdentifierRecall Recall  `json:"identifier_recall"`
	LatencyMS        float64 `json:"latency_ms"`
	ModelLoadMS      float64 `json:"model_load_ms"`
	InferenceMS      float64 `json:"inference_ms"`
	RTF              float64 `json:"real_time_factor"`
	Hallucination    bool    `json:"hallucination"`
}

type SampleResult struct {
	ID       string       `json:"id"`
	Category string       `json:"category"`
	Audio    string       `json:"audio"`
	Skipped  string       `json:"skipped,omitempty"`
	Runs     []ModeResult `json:"runs,omitempty"`
}

type Report struct {
	GeneratedAt time.Time      `json:"generated_at"`
	Samples     []SampleResult `json:"samples"`
}

// Run compares raw Whisper modes with the polished dictation pipeline; a nil
// polished transcriber skips that mode.
func Run(ctx context.Context, transcriber, polished asr.Transcriber, manifest Manifest) Report {
	report := Report{GeneratedAt: time.Now().UTC()}
	for _, sample := range manifest.Samples {
		result := SampleResult{ID: sample.ID, Category: sample.Category, Audio: sample.Audio}
		if _, err := os.Stat(sample.Audio); err != nil {
			result.Skipped = err.Error()
			report.Samples = append(report.Samples, result)
			continue
		}
		result.Runs = append(result.Runs, runMode(ctx, transcriber, sample, "greedy", ""))
		if polished != nil {
			result.Runs = append(result.Runs, runMode(ctx, polished, sample, "polished", ""))
		}
		if len(sample.Hotwords) > 0 {
			hotwords, cleanup, err := hotwordsFile(sample.Hotwords)
			if err != nil {
				result.Runs = append(result.Runs, ModeResult{Mode: "hotwords", Error: err.Error()})
			} else {
				result.Runs = append(result.Runs, runMode(ctx, transcriber, sample, "hotwords", hotwords))
				cleanup()
			}
		}
		report.Samples = append(report.Samples, result)
	}
	return report
}

func runMode(ctx context.Context, transcriber asr.Transcriber, sample Sample, mode, hotwords string) ModeResult {
	request := asr.Request{AudioPath: sample.Audio, HotwordsPath: hotwords, DecodingMethod: "greedy_search"}
	if hotwords != "" {
		request.DecodingMethod = "modified_beam_search"
	}
	transcription, err := transcriber.Transcribe(ctx, request)
	if err != nil {
		return ModeResult{Mode: mode, Error: err.Error()}
	}
	wordError := CalculateWER(sample.Expected, transcription.Text)
	return ModeResult{
		Mode:             mode,
		Transcript:       transcription.Text,
		WER:              wordError.Rate(),
		WordEdits:        wordError.Edits,
		ReferenceWords:   wordError.ReferenceWords,
		TermRecall:       TechnicalTermRecall(transcription.Text, sample.RequiredTerms),
		IdentifierRecall: ExactIdentifierAccuracy(transcription.Text, sample.Identifiers),
		LatencyMS:        float64(transcription.Latency.Microseconds()) / 1000,
		ModelLoadMS:      float64(transcription.ModelLoadLatency.Microseconds()) / 1000,
		InferenceMS:      float64(transcription.InferenceLatency.Microseconds()) / 1000,
		RTF:              transcription.RealTimeFactor,
		Hallucination:    strings.TrimSpace(sample.Expected) == "" && strings.TrimSpace(transcription.Text) != "",
	}
}

func hotwordsFile(words []string) (string, func(), error) {
	f, err := os.CreateTemp("", "vox-hotwords-*.txt")
	if err != nil {
		return "", func() {}, fmt.Errorf("create hotwords file: %w", err)
	}
	name := f.Name()
	cleanup := func() { _ = os.Remove(name) }
	if err := f.Chmod(0o600); err != nil {
		f.Close()
		cleanup()
		return "", func() {}, err
	}
	if _, err := f.WriteString(strings.Join(words, "\n") + "\n"); err != nil {
		f.Close()
		cleanup()
		return "", func() {}, err
	}
	if err := f.Close(); err != nil {
		cleanup()
		return "", func() {}, err
	}
	return name, cleanup, nil
}
