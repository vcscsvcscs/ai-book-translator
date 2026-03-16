package translator

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

const DefaultOllamaURL = "http://localhost:11434"

type ollamaTagsResponse struct {
	Models []ollamaModelEntry `json:"models"`
}

type ollamaModelEntry struct {
	Name string `json:"name"`
}

// ListOllamaModels queries a running Ollama server and returns available model names.
func ListOllamaModels(serverURL string) ([]string, error) {
	if serverURL == "" {
		serverURL = DefaultOllamaURL
	}
	url := strings.TrimRight(serverURL, "/") + "/api/tags"

	resp, err := http.Get(url) //nolint:gosec
	if err != nil {
		return nil, fmt.Errorf("connect to Ollama at %s: %w", serverURL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("Ollama server returned HTTP %d — is it running?", resp.StatusCode)
	}

	var tags ollamaTagsResponse
	if err := json.NewDecoder(resp.Body).Decode(&tags); err != nil {
		return nil, fmt.Errorf("decode Ollama response: %w", err)
	}

	names := make([]string, 0, len(tags.Models))
	for _, m := range tags.Models {
		names = append(names, m.Name)
	}
	return names, nil
}

// NewOllamaBackend creates an LLM backend backed by a running Ollama server.
// Ollama supports the OpenAI-compatible /v1/chat/completions endpoint, so
// we reuse the httpBackend with Ollama's default port.
func NewOllamaBackend(serverURL, modelName string) LLMBackend {
	if serverURL == "" {
		serverURL = DefaultOllamaURL
	}
	return NewHTTPBackend(serverURL, modelName)
}
