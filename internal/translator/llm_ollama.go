package translator

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

const DefaultOllamaURL = "http://localhost:11434"

// Popular Ollama models that users might want to use
// These will be shown in addition to locally installed models
var popularOllamaModels = []string{
	// Translation-optimized models
	"qwen3.5:cloud",
	"qwen3.5:397b-cloud",
	"gpt-oss:20b-cloud",
	"gpt-oss:120b-cloud",
	"qwen2.5:7b",
	"qwen2.5:14b",
	"qwen2.5:32b",
	"qwen2.5:72b",
	"llama3.1:8b",
	"llama3.1:70b",
	"llama3.2:3b",
	"mistral:7b",
	"mixtral:8x7b",
	"gemma2:9b",
	"gemma2:27b",
	"phi3:3.8b",
	"phi3:14b",
	"deepseek-r1:7b",
	"deepseek-r1:14b",
	"deepseek-r1:32b",
	"deepseek-r1:70b",
}

type ollamaTagsResponse struct {
	Models []ollamaModelEntry `json:"models"`
}

type ollamaModelEntry struct {
	Name string `json:"name"`
}

// ListOllamaModels queries a running Ollama server and returns available model names.
// Returns local models first, followed by popular online models that can be pulled.
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

	// Create a map of local models for quick lookup
	localModels := make(map[string]bool)
	names := make([]string, 0, len(tags.Models)+len(popularOllamaModels))
	
	// Add local models first (priority)
	for _, m := range tags.Models {
		names = append(names, m.Name)
		localModels[m.Name] = true
	}
	
	// Add popular online models that aren't already local
	for _, model := range popularOllamaModels {
		if !localModels[model] {
			names = append(names, model)
		}
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
