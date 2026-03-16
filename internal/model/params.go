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

	// ProviderOllama uses a locally running Ollama server (default http://localhost:11434).
	ProviderOllama = "ollama"
	// ProviderDlgoHTTP uses a running dlgo server via its OpenAI-compatible HTTP API.
	ProviderDlgoHTTP = "dlgo-http"
	// ProviderDlgo loads a GGUF file directly via the dlgo library (Linux only).
	ProviderDlgo = "dlgo"
)

type ModelParams struct {
	Temperature    float32 `json:"temperature"`
	MaxTokens      int     `json:"max_tokens"`
	TopK           int     `json:"top_k"`
	TopP           float32 `json:"top_p"`
	ThinkingMode   string  `json:"thinking_mode"`
	ThinkingBudget int     `json:"thinking_budget"`
}

func DefaultModelParams() ModelParams {
	return ModelParams{
		Temperature:    0.3,
		MaxTokens:      2048,
		TopK:           40,
		TopP:           0.9,
		ThinkingMode:   ThinkingDisabled,
		ThinkingBudget: 0,
	}
}
