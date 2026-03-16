package translator

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// TestHTTPBackend_PassesStopAndSeed verifies that Stop and Seed parameters
// are correctly passed to the HTTP backend API.
func TestHTTPBackend_PassesStopAndSeed(t *testing.T) {
	var receivedRequest chatRequest

	// Create a test server that captures the request
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := json.NewDecoder(r.Body).Decode(&receivedRequest); err != nil {
			t.Fatalf("Failed to decode request: %v", err)
		}

		// Send a minimal valid response
		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"test\"}}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()

	backend := NewHTTPBackend(server.URL, "test-model")

	opts := LLMOptions{
		Stop: []string{"\n\nText:", "<|im_end|>"},
		Seed: 42,
	}

	err := backend.ChatStream(context.Background(), "system", "user", func(token string) {}, opts)
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	// Verify Stop tokens were passed
	if len(receivedRequest.Stop) != 2 {
		t.Errorf("Expected 2 stop tokens, got %d", len(receivedRequest.Stop))
	}
	if receivedRequest.Stop[0] != "\n\nText:" {
		t.Errorf("Expected first stop token to be '\\n\\nText:', got '%s'", receivedRequest.Stop[0])
	}
	if receivedRequest.Stop[1] != "<|im_end|>" {
		t.Errorf("Expected second stop token to be '<|im_end|>', got '%s'", receivedRequest.Stop[1])
	}

	// Verify Seed was passed
	if receivedRequest.Seed != 42 {
		t.Errorf("Expected seed to be 42, got %d", receivedRequest.Seed)
	}
}

// TestHTTPBackend_DefaultStopTokens verifies that default stop tokens are used
// when none are provided in LLMOptions.
func TestHTTPBackend_DefaultStopTokens(t *testing.T) {
	var receivedRequest chatRequest

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := json.NewDecoder(r.Body).Decode(&receivedRequest); err != nil {
			t.Fatalf("Failed to decode request: %v", err)
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"test\"}}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()

	backend := NewHTTPBackend(server.URL, "test-model")

	// Empty Stop slice should trigger defaults
	opts := LLMOptions{
		Stop: []string{},
		Seed: 0,
	}

	err := backend.ChatStream(context.Background(), "system", "user", func(token string) {}, opts)
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	// Verify default stop tokens were used
	if len(receivedRequest.Stop) != 2 {
		t.Errorf("Expected 2 default stop tokens, got %d", len(receivedRequest.Stop))
	}
	expectedDefaults := []string{"<|endoftext|>", "<|im_end|>"}
	for i, expected := range expectedDefaults {
		if i >= len(receivedRequest.Stop) {
			t.Errorf("Missing stop token at index %d", i)
			continue
		}
		if receivedRequest.Stop[i] != expected {
			t.Errorf("Expected stop token[%d] to be '%s', got '%s'", i, expected, receivedRequest.Stop[i])
		}
	}
}

// TestHTTPBackend_CustomStopTokens verifies that custom stop tokens override defaults.
func TestHTTPBackend_CustomStopTokens(t *testing.T) {
	var receivedRequest chatRequest

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := json.NewDecoder(r.Body).Decode(&receivedRequest); err != nil {
			t.Fatalf("Failed to decode request: %v", err)
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"test\"}}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()

	backend := NewHTTPBackend(server.URL, "test-model")

	customStops := []string{"STOP", "END"}
	opts := LLMOptions{
		Stop: customStops,
		Seed: 123,
	}

	err := backend.ChatStream(context.Background(), "system", "user", func(token string) {}, opts)
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	// Verify custom stop tokens were used
	if len(receivedRequest.Stop) != len(customStops) {
		t.Errorf("Expected %d stop tokens, got %d", len(customStops), len(receivedRequest.Stop))
	}
	for i, expected := range customStops {
		if i >= len(receivedRequest.Stop) {
			t.Errorf("Missing stop token at index %d", i)
			continue
		}
		if receivedRequest.Stop[i] != expected {
			t.Errorf("Expected stop token[%d] to be '%s', got '%s'", i, expected, receivedRequest.Stop[i])
		}
	}

	// Verify custom seed was passed
	if receivedRequest.Seed != 123 {
		t.Errorf("Expected seed to be 123, got %d", receivedRequest.Seed)
	}
}

// TestOllamaBackend_UsesHTTPBackend verifies that Ollama backend delegates to HTTP backend.
func TestOllamaBackend_UsesHTTPBackend(t *testing.T) {
	var receivedRequest chatRequest

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify the request path is correct for OpenAI-compatible endpoint
		if !strings.HasSuffix(r.URL.Path, "/v1/chat/completions") {
			t.Errorf("Expected path to end with /v1/chat/completions, got %s", r.URL.Path)
		}

		if err := json.NewDecoder(r.Body).Decode(&receivedRequest); err != nil {
			t.Fatalf("Failed to decode request: %v", err)
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("data: {\"choices\":[{\"delta\":{\"content\":\"test\"}}]}\n\n"))
		_, _ = w.Write([]byte("data: [DONE]\n\n"))
	}))
	defer server.Close()

	// NewOllamaBackend should create an HTTP backend
	backend := NewOllamaBackend(server.URL, "qwen:9b")

	opts := LLMOptions{
		Stop: []string{"\n\nText:", "<|im_end|>"},
		Seed: 42,
	}

	err := backend.ChatStream(context.Background(), "system", "user", func(token string) {}, opts)
	if err != nil {
		t.Fatalf("ChatStream failed: %v", err)
	}

	// Verify Stop and Seed were passed through
	if len(receivedRequest.Stop) != 2 {
		t.Errorf("Expected 2 stop tokens, got %d", len(receivedRequest.Stop))
	}
	if receivedRequest.Seed != 42 {
		t.Errorf("Expected seed to be 42, got %d", receivedRequest.Seed)
	}
}
