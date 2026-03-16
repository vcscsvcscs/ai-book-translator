package translator

type LLMBackend interface {
	ChatStream(system, user string, onToken func(string), opts LLMOptions) error
	Close()
}

type LLMOptions struct {
	MaxTokens   int
	Temperature float32
	TopK        int
	TopP        float32
}
