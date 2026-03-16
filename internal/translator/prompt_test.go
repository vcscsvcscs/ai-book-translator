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
