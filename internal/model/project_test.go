package model

import (
	"encoding/json"
	"testing"
	"time"
)

// TestProjectJSONSerialization verifies that new fields serialize and deserialize correctly
func TestProjectJSONSerialization(t *testing.T) {
	// Create a project with all new fields populated
	original := Project{
		ID:               "test-project",
		Name:             "Test Translation",
		SourceFile:       "test.epub",
		SourceFormat:     "epub",
		Provider:         "ollama",
		ProviderURL:      "http://localhost:11434",
		ModelPath:        "qwen:9b",
		SourceLang:       "en",
		TargetLang:       "es",
		StylePrompt:      "Formal style",
		ChunkStrategy:    "sentence",
		ChunkMaxSize:     500,
		ExportFormat:     "epub",
		Status:           StatusCreated,
		CreatedAt:        time.Now(),
		UpdatedAt:        time.Now(),
		GenreContext:     "The text is from a fantasy novel.",
		EnablePolishPass: true,
		MaxContextTokens: 32000,
	}

	// Serialize to JSON
	jsonData, err := json.Marshal(original)
	if err != nil {
		t.Fatalf("Failed to marshal project: %v", err)
	}

	// Deserialize from JSON
	var deserialized Project
	err = json.Unmarshal(jsonData, &deserialized)
	if err != nil {
		t.Fatalf("Failed to unmarshal project: %v", err)
	}

	// Verify new fields
	if deserialized.GenreContext != original.GenreContext {
		t.Errorf("GenreContext mismatch: got %q, want %q", deserialized.GenreContext, original.GenreContext)
	}
	if deserialized.EnablePolishPass != original.EnablePolishPass {
		t.Errorf("EnablePolishPass mismatch: got %v, want %v", deserialized.EnablePolishPass, original.EnablePolishPass)
	}
	if deserialized.MaxContextTokens != original.MaxContextTokens {
		t.Errorf("MaxContextTokens mismatch: got %d, want %d", deserialized.MaxContextTokens, original.MaxContextTokens)
	}
}

// TestBackwardCompatibility verifies that projects without new fields load correctly
func TestBackwardCompatibility(t *testing.T) {
	// JSON from an old project without new fields
	oldProjectJSON := `{
		"id": "old-project",
		"name": "Old Translation",
		"source_file": "old.epub",
		"source_format": "epub",
		"provider": "ollama",
		"provider_url": "http://localhost:11434",
		"model_path": "qwen:9b",
		"source_lang": "en",
		"target_lang": "es",
		"style_prompt": "",
		"chunk_strategy": "sentence",
		"chunk_max_size": 500,
		"model_params": {},
		"export_format": "epub",
		"status": "created",
		"chapters": [],
		"created_at": "2024-01-01T00:00:00Z",
		"updated_at": "2024-01-01T00:00:00Z"
	}`

	var project Project
	err := json.Unmarshal([]byte(oldProjectJSON), &project)
	if err != nil {
		t.Fatalf("Failed to unmarshal old project: %v", err)
	}

	// Verify new fields have zero values (defaults)
	if project.GenreContext != "" {
		t.Errorf("GenreContext should be empty, got %q", project.GenreContext)
	}
	if project.EnablePolishPass != false {
		t.Errorf("EnablePolishPass should be false, got %v", project.EnablePolishPass)
	}
	if project.MaxContextTokens != 0 {
		t.Errorf("MaxContextTokens should be 0, got %d", project.MaxContextTokens)
	}

	// Verify old fields still work
	if project.ID != "old-project" {
		t.Errorf("ID mismatch: got %q, want %q", project.ID, "old-project")
	}
	if project.Name != "Old Translation" {
		t.Errorf("Name mismatch: got %q, want %q", project.Name, "Old Translation")
	}
}
