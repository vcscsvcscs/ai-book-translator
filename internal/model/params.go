package model

const (
	ChunkStrategyParagraph = "paragraph"
	ChunkStrategySentences = "sentences"
	ChunkStrategyTokens    = "tokens"

	ThinkingDisabled = "disabled"
	ThinkingEnabled  = "enabled"
	ThinkingBudget   = "budget"

	FormatEPUB     = "epub"
	FormatPDF      = "pdf"
	FormatMarkdown = "md"

	ProviderOllama   = "ollama"
	ProviderDlgoHTTP = "dlgo-http"
	ProviderDlgo     = "dlgo"
)

type ModelParams struct {
	Temperature       float32 `json:"temperature"`
	MaxTokens         int     `json:"max_tokens"`
	TopK              int     `json:"top_k"`
	TopP              float32 `json:"top_p"`
	MinP              float32 `json:"min_p"`
	PresencePenalty   float32 `json:"presence_penalty"`
	RepetitionPenalty float32 `json:"repetition_penalty"`
	ThinkingMode      string  `json:"thinking_mode"`
	ThinkingBudget    int     `json:"thinking_budget"`
}

func DefaultModelParams() ModelParams {
	return ModelParams{
		Temperature:       0.7,
		MaxTokens:         2048,
		TopK:              20,
		TopP:              0.8,
		MinP:              0.0,
		PresencePenalty:   1.5,
		RepetitionPenalty: 1.0,
		ThinkingMode:      ThinkingDisabled,
		ThinkingBudget:    0,
	}
}

// Qwen3PresetNonThinking returns recommended params for Qwen3 non-thinking general tasks.
func Qwen3PresetNonThinking() ModelParams {
	p := DefaultModelParams()
	p.Temperature = 0.7
	p.TopP = 0.8
	p.TopK = 20
	p.MinP = 0.0
	p.PresencePenalty = 1.5
	p.RepetitionPenalty = 1.0
	p.ThinkingMode = ThinkingDisabled
	return p
}

// Qwen3PresetThinking returns recommended params for Qwen3 thinking general tasks.
func Qwen3PresetThinking() ModelParams {
	p := DefaultModelParams()
	p.Temperature = 1.0
	p.TopP = 0.95
	p.TopK = 20
	p.MinP = 0.0
	p.PresencePenalty = 1.5
	p.RepetitionPenalty = 1.0
	p.ThinkingMode = ThinkingEnabled
	return p
}
