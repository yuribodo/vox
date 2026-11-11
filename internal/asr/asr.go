package asr

import (
	"context"
	"time"
)

type Request struct {
	AudioPath    string
	HotwordsPath string
	// Prompt is literal initial context; Whisper imitates its style and spelling.
	Prompt         string
	DecodingMethod string
}

type Result struct {
	Text             string        `json:"text"`
	AudioDuration    time.Duration `json:"audio_duration"`
	Latency          time.Duration `json:"latency"`
	ModelLoadLatency time.Duration `json:"model_load_latency,omitempty"`
	InferenceLatency time.Duration `json:"inference_latency,omitempty"`
	RealTimeFactor   float64       `json:"real_time_factor"`
}

type Transcriber interface {
	Transcribe(ctx context.Context, request Request) (Result, error)
}
