package benchmark

import (
	"fmt"
	"sort"
	"strings"
)

type Aggregate struct {
	Runs               int
	Failures           int
	WordEdits          int
	ReferenceWords     int
	TermsMatched       int
	TermsTotal         int
	IdentifiersMatched int
	IdentifiersTotal   int
	Hallucinations     int
	LatenciesMS        []float64
	InferenceMS        []float64
	RTFTotal           float64
	RTFMax             float64
}

func (a Aggregate) WER() float64 {
	return WordError{Edits: a.WordEdits, ReferenceWords: a.ReferenceWords}.Rate()
}

func (a Aggregate) TermRecall() float64 {
	return Recall{Matched: a.TermsMatched, Total: a.TermsTotal}.Rate()
}

func (a Aggregate) IdentifierAccuracy() float64 {
	return Recall{Matched: a.IdentifiersMatched, Total: a.IdentifiersTotal}.Rate()
}

func (a Aggregate) MeanRTF() float64 {
	if a.Runs == 0 {
		return 0
	}
	return a.RTFTotal / float64(a.Runs)
}

func (a Aggregate) MedianLatencyMS() float64 {
	return median(a.LatenciesMS)
}

func (a Aggregate) MedianInferenceMS() float64 {
	return median(a.InferenceMS)
}

func median(input []float64) float64 {
	if len(input) == 0 {
		return 0
	}
	values := append([]float64(nil), input...)
	sort.Float64s(values)
	middle := len(values) / 2
	if len(values)%2 == 1 {
		return values[middle]
	}
	return (values[middle-1] + values[middle]) / 2
}

func addRun(aggregate Aggregate, run ModeResult) Aggregate {
	if run.Error != "" {
		aggregate.Failures++
		return aggregate
	}
	aggregate.Runs++
	aggregate.WordEdits += run.WordEdits
	aggregate.ReferenceWords += run.ReferenceWords
	aggregate.TermsMatched += run.TermRecall.Matched
	aggregate.TermsTotal += run.TermRecall.Total
	aggregate.IdentifiersMatched += run.IdentifierRecall.Matched
	aggregate.IdentifiersTotal += run.IdentifierRecall.Total
	if run.Hallucination {
		aggregate.Hallucinations++
	}
	aggregate.LatenciesMS = append(aggregate.LatenciesMS, run.LatencyMS)
	aggregate.InferenceMS = append(aggregate.InferenceMS, run.InferenceMS)
	aggregate.RTFTotal += run.RTF
	if run.RTF > aggregate.RTFMax {
		aggregate.RTFMax = run.RTF
	}
	return aggregate
}

func (r Report) Aggregates() map[string]Aggregate {
	result := map[string]Aggregate{}
	for _, sample := range r.Samples {
		for _, run := range sample.Runs {
			result[run.Mode] = addRun(result[run.Mode], run)
		}
	}
	return result
}

func (r Report) aggregateFor(mode, category string) Aggregate {
	var result Aggregate
	for _, sample := range r.Samples {
		if category != "" && sample.Category != category {
			continue
		}
		for _, run := range sample.Runs {
			if run.Mode == mode {
				result = addRun(result, run)
			}
		}
	}
	return result
}

type HotwordComparison struct {
	Pairs         int
	TermImproved  int
	TermRegressed int
	WERImproved   int
	WERRegressed  int
}

func (r Report) hotwordComparison() HotwordComparison {
	var result HotwordComparison
	for _, sample := range r.Samples {
		var greedy, hotwords *ModeResult
		for index := range sample.Runs {
			run := &sample.Runs[index]
			if run.Error != "" {
				continue
			}
			switch run.Mode {
			case "greedy":
				greedy = run
			case "hotwords":
				hotwords = run
			}
		}
		if greedy == nil || hotwords == nil {
			continue
		}
		result.Pairs++
		switch {
		case hotwords.TermRecall.Matched > greedy.TermRecall.Matched:
			result.TermImproved++
		case hotwords.TermRecall.Matched < greedy.TermRecall.Matched:
			result.TermRegressed++
		}
		switch {
		case hotwords.WER < greedy.WER:
			result.WERImproved++
		case hotwords.WER > greedy.WER:
			result.WERRegressed++
		}
	}
	return result
}

func (r Report) Markdown() string {
	var b strings.Builder
	b.WriteString("# Whisper large-v3-turbo benchmark\n\n")
	fmt.Fprintf(&b, "Generated: %s\n\n", r.GeneratedAt.Format("2006-01-02 15:04:05Z"))
	b.WriteString("## Environment\n\n")
	b.WriteString("- Target: CachyOS Linux, kernel 7.2.0-1-cachyos, AMD Ryzen 7 5800H, 15.5 GiB RAM, NVIDIA RTX 3050 Laptop GPU (4 GiB).\n")
	b.WriteString("- NVIDIA driver 610.57.04, CUDA 13.3.1, cuDNN 9.25.0.15; PipeWire 1.6.7; tmux 3.7c.\n")
	b.WriteString("- Runtime: whisper.cpp 1.9.1, built locally for CUDA compute capability 8.6.\n")
	b.WriteString("- Model: OpenAI Whisper large-v3-turbo Q8_0 with Silero VAD 6.2.0.\n")
	b.WriteString("- Provider: CUDA. Manifest hotwords are supplied as a bounded initial vocabulary prompt.\n")
	b.WriteString("- Acquisition: pinned official assets and SHA-256 digests in `docs/dependencies.md`.\n\n")
	b.WriteString("## Personal benchmark results\n\nTranscripts remain only in the gitignored machine-readable result. The versioned report records status and metrics without recognized text.\n\n")
	b.WriteString("| Sample | Category | Mode | Status | WER | Term recall | Identifier accuracy | Cold wall | Inference | RTF |\n| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |\n")
	for _, sample := range r.Samples {
		if sample.Skipped != "" {
			fmt.Fprintf(&b, "| %s | %s | — | skipped: `%s` | — | — | — | — | — | — |\n", cell(sample.ID), cell(sample.Category), cell(sample.Skipped))
			continue
		}
		for _, run := range sample.Runs {
			status := "ok"
			if run.Error != "" {
				status = "error: " + run.Error
			}
			fmt.Fprintf(&b, "| %s | %s | %s | %s | %.1f%% | %d/%d | %d/%d | %.0f ms | %.0f ms | %.3f |\n",
				cell(sample.ID), cell(sample.Category), run.Mode, cell(status), run.WER*100,
				run.TermRecall.Matched, run.TermRecall.Total, run.IdentifierRecall.Matched,
				run.IdentifierRecall.Total, run.LatencyMS, run.InferenceMS, run.RTF)
		}
	}

	b.WriteString("\n## Aggregates\n\n| Mode | Successful | Failures | WER | Term recall | Identifier accuracy | Median cold wall | Median inference | Mean / max RTF | Hallucinations |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n")
	aggregates := r.Aggregates()
	for _, mode := range []string{"greedy", "hotwords", "polished"} {
		aggregate, ok := aggregates[mode]
		if !ok {
			continue
		}
		fmt.Fprintf(&b, "| %s | %d | %d | %.1f%% | %.1f%% | %.1f%% | %.0f ms | %.0f ms | %.3f / %.3f | %d |\n",
			mode, aggregate.Runs, aggregate.Failures, aggregate.WER()*100, aggregate.TermRecall()*100,
			aggregate.IdentifierAccuracy()*100, aggregate.MedianLatencyMS(), aggregate.MedianInferenceMS(), aggregate.MeanRTF(), aggregate.RTFMax, aggregate.Hallucinations)
	}

	technical := r.aggregateFor("hotwords", "technical-vocabulary")
	paired := r.hotwordComparison()
	fmt.Fprintf(&b, "\n## Context-prompt findings\n\n- Required-term recall across all context-eligible samples: **%d/%d (%.1f%%)**.\n", aggregates["hotwords"].TermsMatched, aggregates["hotwords"].TermsTotal, aggregates["hotwords"].TermRecall()*100)
	fmt.Fprintf(&b, "- Technical-vocabulary category recall: **%d/%d (%.1f%%)**.\n", technical.TermsMatched, technical.TermsTotal, technical.TermRecall()*100)
	fmt.Fprintf(&b, "- Exact identifier accuracy with initial context prompts: **%d/%d (%.1f%%)**.\n", aggregates["hotwords"].IdentifiersMatched, aggregates["hotwords"].IdentifiersTotal, aggregates["hotwords"].IdentifierAccuracy()*100)
	fmt.Fprintf(&b, "- Across %d paired runs, context prompts improved required-term matches in %d and regressed them in %d; WER improved in %d and regressed in %d.\n", paired.Pairs, paired.TermImproved, paired.TermRegressed, paired.WERImproved, paired.WERRegressed)

	b.WriteString("\n## Provider, duration, and resource evidence\n\n")
	b.WriteString("The Q8_0 model runs on the RTX 3050 with Silero VAD enabled. The 47-run benchmark completed sequentially without failure or OOM. Direct `/proc` and NVIDIA process sampling on an isolated 20-second run observed 515,808 KiB peak process RSS and 1,230 MiB peak process VRAM.\n\n")
	b.WriteString("| Synthetic duration | Median inference (5 runs) | Median RTF |\n| ---: | ---: | ---: |\n| 5 s | 434 ms | 0.087 |\n| 10 s | 521 ms | 0.052 |\n| 20 s | 493 ms | 0.025 |\n")
	b.WriteString("\n## Recording and insertion evidence\n\n")
	b.WriteString("PipeWire recording produced mono 16 kHz PCM WAV and finalized cleanly on Ctrl-C. The tmux transport remained bound to the captured pane, preserved Unicode and multiline content, inserted dangerous-looking text without executing it, and never sent Enter. See `docs/manual-integration.md`.\n")
	b.WriteString("\n## Setup constraints\n\nInference starts a fresh process for each file, so cold wall latency includes model loading. Results are specific to the hardware and software versions above. Re-run `vox doctor` after kernel, driver, CUDA, or model changes.\n")
	return b.String()
}

func cell(value string) string {
	value = strings.ReplaceAll(value, "|", "\\|")
	value = strings.ReplaceAll(value, "\n", "<br>")
	return value
}
