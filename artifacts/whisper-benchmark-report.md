# Whisper large-v3-turbo benchmark

Generated: 2026-11-11 01:02:10Z

## Environment

- Target: CachyOS Linux, kernel 7.2.0-1-cachyos, AMD Ryzen 7 5800H, 15.5 GiB RAM, NVIDIA RTX 3050 Laptop GPU (4 GiB).
- NVIDIA driver 610.57.04, CUDA 13.3.1, cuDNN 9.25.0.15; PipeWire 1.6.7; tmux 3.7c.
- Runtime: whisper.cpp 1.9.1, built locally for CUDA compute capability 8.6.
- Model: OpenAI Whisper large-v3-turbo Q8_0 with Silero VAD 6.2.0.
- Provider: CUDA. Manifest hotwords are supplied as a bounded initial vocabulary prompt.
- Acquisition: pinned official assets and SHA-256 digests in `docs/dependencies.md`.

## Personal benchmark results

Transcripts remain only in the gitignored machine-readable result. The versioned report records status and metrics without recognized text.

| Sample | Category | Mode | Status | WER | Term recall | Identifier accuracy | Cold wall | Inference | RTF |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| natural-001 | natural-prompt | greedy | ok | 9.1% | 0/0 | 0/0 | 1069 ms | 409 ms | 0.032 |
| natural-001 | natural-prompt | polished | ok | 0.0% | 0/0 | 0/0 | 1685 ms | 402 ms | 0.031 |
| natural-002 | natural-prompt | greedy | ok | 7.7% | 0/0 | 0/0 | 921 ms | 392 ms | 0.043 |
| natural-002 | natural-prompt | polished | ok | 7.7% | 0/0 | 0/0 | 1672 ms | 402 ms | 0.044 |
| natural-003 | natural-prompt | greedy | ok | 8.3% | 0/0 | 0/0 | 924 ms | 400 ms | 0.034 |
| natural-003 | natural-prompt | polished | ok | 8.3% | 0/0 | 0/0 | 1721 ms | 411 ms | 0.035 |
| natural-004 | natural-prompt | greedy | ok | 0.0% | 0/0 | 0/0 | 963 ms | 410 ms | 0.066 |
| natural-004 | natural-prompt | polished | ok | 0.0% | 0/0 | 0/0 | 1676 ms | 392 ms | 0.063 |
| natural-005 | natural-prompt | greedy | ok | 0.0% | 0/0 | 0/0 | 922 ms | 379 ms | 0.074 |
| natural-005 | natural-prompt | polished | ok | 0.0% | 0/0 | 0/0 | 1662 ms | 380 ms | 0.074 |
| natural-006 | natural-prompt | greedy | ok | 0.0% | 0/0 | 0/0 | 946 ms | 376 ms | 0.069 |
| natural-006 | natural-prompt | polished | ok | 0.0% | 0/0 | 0/0 | 1627 ms | 378 ms | 0.070 |
| natural-007 | natural-prompt | greedy | ok | 10.0% | 0/0 | 0/0 | 910 ms | 377 ms | 0.062 |
| natural-007 | natural-prompt | polished | ok | 10.0% | 0/0 | 0/0 | 1637 ms | 378 ms | 0.062 |
| natural-008 | natural-prompt | greedy | ok | 12.5% | 0/0 | 0/0 | 917 ms | 379 ms | 0.065 |
| natural-008 | natural-prompt | polished | ok | 12.5% | 0/0 | 0/0 | 1641 ms | 382 ms | 0.066 |
| natural-009 | natural-prompt | greedy | ok | 0.0% | 0/0 | 0/0 | 926 ms | 380 ms | 0.067 |
| natural-009 | natural-prompt | polished | ok | 0.0% | 0/0 | 0/0 | 1658 ms | 380 ms | 0.067 |
| natural-010 | natural-prompt | greedy | ok | 0.0% | 0/0 | 0/0 | 924 ms | 390 ms | 0.056 |
| natural-010 | natural-prompt | polished | ok | 0.0% | 0/0 | 0/0 | 1686 ms | 394 ms | 0.056 |
| technical-001 | technical-vocabulary | greedy | ok | 0.0% | 2/2 | 0/0 | 914 ms | 384 ms | 0.067 |
| technical-001 | technical-vocabulary | polished | ok | 0.0% | 2/2 | 0/0 | 1654 ms | 390 ms | 0.068 |
| technical-001 | technical-vocabulary | hotwords | ok | 0.0% | 2/2 | 0/0 | 946 ms | 384 ms | 0.067 |
| technical-002 | technical-vocabulary | greedy | ok | 0.0% | 1/1 | 0/0 | 965 ms | 415 ms | 0.074 |
| technical-002 | technical-vocabulary | polished | ok | 0.0% | 1/1 | 0/0 | 1712 ms | 421 ms | 0.075 |
| technical-002 | technical-vocabulary | hotwords | ok | 0.0% | 1/1 | 0/0 | 960 ms | 407 ms | 0.073 |
| technical-003 | technical-vocabulary | greedy | ok | 0.0% | 2/2 | 0/0 | 925 ms | 390 ms | 0.070 |
| technical-003 | technical-vocabulary | polished | ok | 0.0% | 2/2 | 0/0 | 1701 ms | 386 ms | 0.069 |
| technical-003 | technical-vocabulary | hotwords | ok | 0.0% | 2/2 | 0/0 | 992 ms | 420 ms | 0.075 |
| technical-004 | technical-vocabulary | greedy | ok | 0.0% | 1/1 | 0/0 | 913 ms | 379 ms | 0.069 |
| technical-004 | technical-vocabulary | polished | ok | 10.0% | 1/1 | 0/0 | 1713 ms | 384 ms | 0.070 |
| technical-004 | technical-vocabulary | hotwords | ok | 0.0% | 1/1 | 0/0 | 917 ms | 397 ms | 0.073 |
| technical-005 | technical-vocabulary | greedy | ok | 0.0% | 2/2 | 0/0 | 955 ms | 406 ms | 0.072 |
| technical-005 | technical-vocabulary | polished | ok | 0.0% | 2/2 | 0/0 | 1629 ms | 384 ms | 0.068 |
| technical-005 | technical-vocabulary | hotwords | ok | 0.0% | 2/2 | 0/0 | 966 ms | 426 ms | 0.076 |
| technical-006 | technical-vocabulary | greedy | ok | 37.5% | 0/2 | 0/0 | 971 ms | 396 ms | 0.081 |
| technical-006 | technical-vocabulary | polished | ok | 12.5% | 1/2 | 0/0 | 1650 ms | 387 ms | 0.079 |
| technical-006 | technical-vocabulary | hotwords | ok | 12.5% | 2/2 | 0/0 | 995 ms | 393 ms | 0.080 |
| technical-007 | technical-vocabulary | greedy | ok | 14.3% | 2/2 | 0/0 | 913 ms | 377 ms | 0.081 |
| technical-007 | technical-vocabulary | polished | ok | 14.3% | 2/2 | 0/0 | 1624 ms | 377 ms | 0.081 |
| technical-007 | technical-vocabulary | hotwords | ok | 14.3% | 2/2 | 0/0 | 953 ms | 373 ms | 0.080 |
| technical-008 | technical-vocabulary | greedy | ok | 22.2% | 1/2 | 0/0 | 959 ms | 382 ms | 0.073 |
| technical-008 | technical-vocabulary | polished | ok | 11.1% | 2/2 | 0/0 | 1731 ms | 381 ms | 0.073 |
| technical-008 | technical-vocabulary | hotwords | ok | 22.2% | 1/2 | 0/0 | 933 ms | 379 ms | 0.073 |
| identifier-001 | identifier | greedy | ok | 54.5% | 0/1 | 0/1 | 926 ms | 394 ms | 0.057 |
| identifier-001 | identifier | polished | ok | 54.5% | 0/1 | 0/1 | 1710 ms | 397 ms | 0.057 |
| identifier-001 | identifier | hotwords | ok | 27.3% | 1/1 | 1/1 | 961 ms | 418 ms | 0.060 |
| identifier-002 | identifier | greedy | ok | 12.5% | 2/2 | 2/2 | 980 ms | 408 ms | 0.074 |
| identifier-002 | identifier | polished | ok | 12.5% | 2/2 | 2/2 | 1637 ms | 388 ms | 0.070 |
| identifier-002 | identifier | hotwords | ok | 12.5% | 2/2 | 2/2 | 931 ms | 390 ms | 0.070 |
| identifier-003 | identifier | greedy | ok | 38.5% | 0/0 | 0/0 | 942 ms | 397 ms | 0.054 |
| identifier-003 | identifier | polished | ok | 38.5% | 0/0 | 0/0 | 1646 ms | 399 ms | 0.055 |
| identifier-003 | identifier | hotwords | ok | 30.8% | 0/0 | 0/0 | 928 ms | 401 ms | 0.055 |
| identifier-004 | identifier | greedy | ok | 28.6% | 0/0 | 0/0 | 951 ms | 371 ms | 0.060 |
| identifier-004 | identifier | polished | ok | 28.6% | 0/0 | 0/0 | 1603 ms | 379 ms | 0.061 |
| identifier-004 | identifier | hotwords | ok | 28.6% | 0/0 | 0/0 | 910 ms | 375 ms | 0.061 |
| identifier-005 | identifier | greedy | ok | 175.0% | 0/2 | 0/2 | 936 ms | 383 ms | 0.070 |
| identifier-005 | identifier | polished | ok | 150.0% | 0/2 | 0/2 | 1664 ms | 391 ms | 0.071 |
| identifier-005 | identifier | hotwords | ok | 50.0% | 2/2 | 2/2 | 1004 ms | 417 ms | 0.076 |
| hesitation-001 | hesitation | greedy | ok | 8.3% | 1/1 | 0/0 | 941 ms | 390 ms | 0.067 |
| hesitation-001 | hesitation | polished | ok | 41.7% | 1/1 | 0/0 | 1648 ms | 395 ms | 0.068 |
| hesitation-001 | hesitation | hotwords | ok | 0.0% | 1/1 | 0/0 | 924 ms | 391 ms | 0.067 |
| hesitation-002 | hesitation | greedy | ok | 11.1% | 0/1 | 0/0 | 941 ms | 386 ms | 0.082 |
| hesitation-002 | hesitation | polished | ok | 33.3% | 1/1 | 0/0 | 1650 ms | 386 ms | 0.082 |
| hesitation-002 | hesitation | hotwords | ok | 0.0% | 1/1 | 0/0 | 966 ms | 387 ms | 0.082 |
| hesitation-003 | hesitation | greedy | ok | 10.0% | 2/2 | 0/0 | 920 ms | 384 ms | 0.067 |
| hesitation-003 | hesitation | polished | ok | 10.0% | 2/2 | 0/0 | 1646 ms | 393 ms | 0.068 |
| hesitation-003 | hesitation | hotwords | ok | 10.0% | 2/2 | 0/0 | 925 ms | 389 ms | 0.068 |
| hesitation-004 | hesitation | greedy | ok | 15.4% | 0/1 | 0/1 | 970 ms | 404 ms | 0.064 |
| hesitation-004 | hesitation | polished | ok | 30.8% | 1/1 | 1/1 | 1706 ms | 409 ms | 0.065 |
| hesitation-004 | hesitation | hotwords | ok | 30.8% | 1/1 | 1/1 | 938 ms | 388 ms | 0.062 |
| silence-001 | silence-noise | greedy | ok | 0.0% | 0/0 | 0/0 | 601 ms | 28 ms | 0.004 |
| silence-001 | silence-noise | polished | ok | 0.0% | 0/0 | 0/0 | 549 ms | 20 ms | 0.003 |
| silence-002 | silence-noise | greedy | ok | 0.0% | 0/0 | 0/0 | 549 ms | 24 ms | 0.004 |
| silence-002 | silence-noise | polished | ok | 0.0% | 0/0 | 0/0 | 540 ms | 20 ms | 0.003 |
| silence-003 | silence-noise | greedy | ok | 0.0% | 0/0 | 0/0 | 576 ms | 26 ms | 0.004 |
| silence-003 | silence-noise | polished | ok | 0.0% | 0/0 | 0/0 | 538 ms | 20 ms | 0.003 |

## Aggregates

| Mode | Successful | Failures | WER | Term recall | Identifier accuracy | Median cold wall | Median inference | Mean / max RTF | Hallucinations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| greedy | 30 | 0 | 14.0% | 66.7% | 33.3% | 926 ms | 385 ms | 0.059 / 0.082 | 0 |
| hotwords | 17 | 0 | 13.1% | 95.8% | 100.0% | 946 ms | 391 ms | 0.070 / 0.082 | 0 |
| polished | 30 | 0 | 15.5% | 83.3% | 50.0% | 1652 ms | 387 ms | 0.059 / 0.082 | 0 |

## Context-prompt findings

- Required-term recall across all context-eligible samples: **23/24 (95.8%)**.
- Technical-vocabulary category recall: **13/14 (92.9%)**.
- Exact identifier accuracy with initial context prompts: **6/6 (100.0%)**.
- Across 17 paired runs, context prompts improved required-term matches in 5 and regressed them in 0; WER improved in 6 and regressed in 1.

## Provider, duration, and resource evidence

The Q8_0 model runs on the RTX 3050 with Silero VAD enabled. The 47-run benchmark completed sequentially without failure or OOM. Direct `/proc` and NVIDIA process sampling on an isolated 20-second run observed 515,808 KiB peak process RSS and 1,230 MiB peak process VRAM.

| Synthetic duration | Median inference (5 runs) | Median RTF |
| ---: | ---: | ---: |
| 5 s | 434 ms | 0.087 |
| 10 s | 521 ms | 0.052 |
| 20 s | 493 ms | 0.025 |

## Recording and insertion evidence

PipeWire recording produced mono 16 kHz PCM WAV and finalized cleanly on Ctrl-C. The tmux transport remained bound to the captured pane, preserved Unicode and multiline content, inserted dangerous-looking text without executing it, and never sent Enter. See `docs/manual-integration.md`.

## Setup constraints

Inference starts a fresh process for each file, so cold wall latency includes model loading. Results are specific to the hardware and software versions above. Re-run `vox doctor` after kernel, driver, CUDA, or model changes.
