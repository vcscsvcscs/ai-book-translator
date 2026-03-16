package translator

import "context"

type LLMBackend interface {
	ChatStream(ctx context.Context, system, user string, onToken func(string), opts LLMOptions) error
	Close()
}

type LLMOptions struct {
	MaxTokens         int
	Temperature       float32
	TopK              int
	TopP              float32
	MinP              float32
	PresencePenalty   float32
	RepetitionPenalty float32
	ThinkingMode      string   // model.ThinkingDisabled / Enabled / Budget
	Stop              []string // Stop sequences to prevent over-generation
	Seed              int      // Deterministic seed for reproducibility
}
