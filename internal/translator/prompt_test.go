package translator

import (
	"strings"
	"testing"
)

func TestBuildSystemPrompt_AccuracyFocusedRules(t *testing.T) {
	tests := []struct {
		name        string
		sourceLang  string
		targetLang  string
		stylePrompt string
	}{
		{
			name:        "English to Chinese",
			sourceLang:  "en",
			targetLang:  "zh",
			stylePrompt: "",
		},
		{
			name:        "Japanese to English",
			sourceLang:  "ja",
			targetLang:  "en",
			stylePrompt: "",
		},
		{
			name:        "German to French",
			sourceLang:  "de",
			targetLang:  "fr",
			stylePrompt: "",
		},
		{
			name:        "Spanish to Portuguese",
			sourceLang:  "es",
			targetLang:  "pt",
			stylePrompt: "",
		},
		{
			name:        "Korean to English with style",
			sourceLang:  "ko",
			targetLang:  "en",
			stylePrompt: "Use formal tone",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			prompt := BuildSystemPrompt(tt.sourceLang, tt.targetLang, tt.stylePrompt)

			// Verify accuracy-focused rules are present
			requiredRules := []string{
				"Output ONLY the translated text",
				"Do NOT add commentary, explanations, or notes",
				"Do NOT include the original text",
				"Preserve the exact meaning of every sentence",
				"Do NOT invent or replace objects, locations, or actions",
				"Maintain the original paragraph structure",
				"Keep character names and proper nouns unchanged",
				"Prefer accuracy over creativity",
			}

			for _, rule := range requiredRules {
				if !strings.Contains(prompt, rule) {
					t.Errorf("Expected prompt to contain rule: %q", rule)
				}
			}
		})
	}
}

func TestBuildSystemPrompt_AntiHallucinationGuard(t *testing.T) {
	prompt := BuildSystemPrompt("en", "zh", "")

	antiHallucinationRule := "If a sentence is unclear, translate it literally rather than guessing"
	if !strings.Contains(prompt, antiHallucinationRule) {
		t.Errorf("Expected prompt to contain anti-hallucination guard: %q", antiHallucinationRule)
	}
}

func TestBuildSystemPrompt_PreservesStylePrompt(t *testing.T) {
	stylePrompt := "Use formal, academic tone"
	prompt := BuildSystemPrompt("en", "fr", stylePrompt)

	if !strings.Contains(prompt, "Style:") {
		t.Error("Expected prompt to contain 'Style:' section")
	}

	if !strings.Contains(prompt, stylePrompt) {
		t.Errorf("Expected prompt to contain style prompt: %q", stylePrompt)
	}
}

func TestBuildSystemPrompt_NoStylePrompt(t *testing.T) {
	prompt := BuildSystemPrompt("en", "de", "")

	// Should not contain Style: section when stylePrompt is empty
	if strings.Contains(prompt, "Style:") {
		t.Error("Expected prompt to NOT contain 'Style:' section when stylePrompt is empty")
	}
}

func TestBuildSystemPrompt_LanguageNames(t *testing.T) {
	tests := []struct {
		sourceLang string
		targetLang string
		wantSource string
		wantTarget string
	}{
		{"en", "zh", "English", "Chinese"},
		{"ja", "en", "Japanese", "English"},
		{"de", "fr", "German", "French"},
		{"ko", "es", "Korean", "Spanish"},
	}

	for _, tt := range tests {
		t.Run(tt.sourceLang+"_to_"+tt.targetLang, func(t *testing.T) {
			prompt := BuildSystemPrompt(tt.sourceLang, tt.targetLang, "")

			if !strings.Contains(prompt, tt.wantSource) {
				t.Errorf("Expected prompt to contain source language name: %q", tt.wantSource)
			}

			if !strings.Contains(prompt, tt.wantTarget) {
				t.Errorf("Expected prompt to contain target language name: %q", tt.wantTarget)
			}
		})
	}
}

func TestBuildUserMessage_WithoutGenreContext(t *testing.T) {
	sourceLang := "en"
	targetLang := "zh"
	text := "This is a test sentence."
	genreContext := ""

	userMsg := BuildUserMessage(sourceLang, targetLang, text, genreContext)

	// Verify faithful translation instructions are present
	if !strings.Contains(userMsg, "Translate faithfully and preserve the meaning of every sentence") {
		t.Error("Expected user message to contain faithful translation instruction")
	}

	if !strings.Contains(userMsg, "Do not summarize or invent new details") {
		t.Error("Expected user message to contain warning against summarizing")
	}

	// Verify language names are present
	if !strings.Contains(userMsg, "English") {
		t.Error("Expected user message to contain source language name")
	}

	if !strings.Contains(userMsg, "Chinese") {
		t.Error("Expected user message to contain target language name")
	}

	// Verify text is present with "Text:" label
	if !strings.Contains(userMsg, "Text:\n") {
		t.Error("Expected user message to contain 'Text:' label")
	}

	if !strings.Contains(userMsg, text) {
		t.Error("Expected user message to contain the source text")
	}

	// Verify no genre context is present
	if strings.Contains(userMsg, "fantasy") || strings.Contains(userMsg, "novel") {
		t.Error("Expected user message to NOT contain genre context when not provided")
	}
}

func TestBuildUserMessage_WithGenreContext(t *testing.T) {
	sourceLang := "en"
	targetLang := "zh"
	text := "The carriage rolled through the village."
	genreContext := "The text is from a fantasy novel."

	userMsg := BuildUserMessage(sourceLang, targetLang, text, genreContext)

	// Verify genre context is present
	if !strings.Contains(userMsg, genreContext) {
		t.Errorf("Expected user message to contain genre context: %q", genreContext)
	}

	// Verify genre context appears before "Text:" section
	genreIdx := strings.Index(userMsg, genreContext)
	textIdx := strings.Index(userMsg, "Text:\n")

	if genreIdx == -1 {
		t.Error("Genre context not found in user message")
	}

	if textIdx == -1 {
		t.Error("'Text:' label not found in user message")
	}

	if genreIdx >= textIdx {
		t.Error("Expected genre context to appear before 'Text:' section")
	}

	// Verify faithful translation instructions are still present
	if !strings.Contains(userMsg, "Translate faithfully") {
		t.Error("Expected user message to contain faithful translation instruction")
	}

	// Verify text is present
	if !strings.Contains(userMsg, text) {
		t.Error("Expected user message to contain the source text")
	}
}

func TestBuildUserMessage_VariousLanguagePairs(t *testing.T) {
	tests := []struct {
		name       string
		sourceLang string
		targetLang string
		wantSource string
		wantTarget string
	}{
		{
			name:       "English to Japanese",
			sourceLang: "en",
			targetLang: "ja",
			wantSource: "English",
			wantTarget: "Japanese",
		},
		{
			name:       "German to Spanish",
			sourceLang: "de",
			targetLang: "es",
			wantSource: "German",
			wantTarget: "Spanish",
		},
		{
			name:       "Korean to French",
			sourceLang: "ko",
			targetLang: "fr",
			wantSource: "Korean",
			wantTarget: "French",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			text := "Sample text for translation."
			userMsg := BuildUserMessage(tt.sourceLang, tt.targetLang, text, "")

			if !strings.Contains(userMsg, tt.wantSource) {
				t.Errorf("Expected user message to contain source language: %q", tt.wantSource)
			}

			if !strings.Contains(userMsg, tt.wantTarget) {
				t.Errorf("Expected user message to contain target language: %q", tt.wantTarget)
			}
		})
	}
}

func TestBuildUserMessage_EmptyGenreContext(t *testing.T) {
	sourceLang := "en"
	targetLang := "zh"
	text := "Test text."
	genreContext := ""

	userMsg := BuildUserMessage(sourceLang, targetLang, text, genreContext)

	// Count occurrences of "Text:" - should only appear once
	count := strings.Count(userMsg, "Text:")
	if count != 1 {
		t.Errorf("Expected 'Text:' to appear exactly once, got %d occurrences", count)
	}

	// Verify no extra blank lines before "Text:"
	lines := strings.Split(userMsg, "\n")
	foundText := false
	consecutiveEmpty := 0

	for _, line := range lines {
		if strings.TrimSpace(line) == "" {
			consecutiveEmpty++
		} else {
			if strings.HasPrefix(line, "Text:") {
				foundText = true
				// Should have at most 2 consecutive empty lines before "Text:"
				// (one after instructions, one as separator)
				if consecutiveEmpty > 2 {
					t.Errorf("Expected at most 2 empty lines before 'Text:', got %d", consecutiveEmpty)
				}
			}
			consecutiveEmpty = 0
		}
	}

	if !foundText {
		t.Error("Expected to find 'Text:' label in user message")
	}
}
