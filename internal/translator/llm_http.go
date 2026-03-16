package translator

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
)

type httpBackend struct {
	baseURL string
	model   string
	client  *http.Client
}

func NewHTTPBackend(serverURL, modelName string) LLMBackend {
	return &httpBackend{
		baseURL: strings.TrimRight(serverURL, "/"),
		model:   modelName,
		client:  &http.Client{},
	}
}

type chatRequest struct {
	Model    string        `json:"model"`
	Messages []chatMessage `json:"messages"`
	Stream   bool          `json:"stream"`
	Stop     []string      `json:"stop,omitempty"`
	// Top-level OpenAI-compatible fields
	Temperature       float32  `json:"temperature,omitempty"`
	MaxTokens         int      `json:"max_tokens,omitempty"`
	TopP              float32  `json:"top_p,omitempty"`
	PresencePenalty   float32  `json:"presence_penalty,omitempty"`
	RepetitionPenalty float32  `json:"repetition_penalty,omitempty"`
	// Ollama extra params go in the options object
	Options *chatOptions `json:"options,omitempty"`
}

type chatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// chatOptions carries Ollama-specific sampling params that aren't in the OpenAI spec.
type chatOptions struct {
	TopK     float32 `json:"top_k,omitempty"`
	MinP     float32 `json:"min_p,omitempty"`
	Thinking *bool   `json:"thinking,omitempty"` // Ollama >= 0.9 Qwen3 thinking toggle
}

type streamChunk struct {
	Choices []streamChoice `json:"choices"`
}

type streamChoice struct {
	Delta streamDelta `json:"delta"`
}

type streamDelta struct {
	Content string `json:"content"`
}

func (h *httpBackend) ChatStream(ctx context.Context, system, user string, onToken func(string), opts LLMOptions) error {
	var messages []chatMessage
	if system != "" {
		messages = append(messages, chatMessage{Role: "system", Content: system})
	}
	messages = append(messages, chatMessage{Role: "user", Content: user})

	// Use native Ollama thinking toggle instead of /think directive in the prompt.
	thinkingOn := opts.ThinkingMode == "enabled" || opts.ThinkingMode == "budget"
	thinkingFlag := &thinkingOn

	reqBody := chatRequest{
		Model:             h.model,
		Messages:          messages,
		Stream:            true,
		Stop:              []string{"<|endoftext|>", "<|im_end|>"},
		Temperature:       opts.Temperature,
		MaxTokens:         opts.MaxTokens,
		TopP:              opts.TopP,
		PresencePenalty:   opts.PresencePenalty,
		RepetitionPenalty: opts.RepetitionPenalty,
		Options: &chatOptions{
			TopK:     float32(opts.TopK),
			MinP:     opts.MinP,
			Thinking: thinkingFlag,
		},
	}

	body, err := json.Marshal(reqBody)
	if err != nil {
		return fmt.Errorf("marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", h.baseURL+"/v1/chat/completions", bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := h.client.Do(req)
	if err != nil {
		return fmt.Errorf("http request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("server returned %d: %s", resp.StatusCode, string(respBody))
	}

	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		line := scanner.Text()
		if !strings.HasPrefix(line, "data: ") {
			continue
		}
		data := strings.TrimPrefix(line, "data: ")
		if data == "[DONE]" {
			break
		}

		var chunk streamChunk
		if err := json.Unmarshal([]byte(data), &chunk); err != nil {
			continue
		}

		for _, choice := range chunk.Choices {
			if choice.Delta.Content != "" {
				onToken(choice.Delta.Content)
			}
		}
	}

	return scanner.Err()
}

func (h *httpBackend) Close() {}
