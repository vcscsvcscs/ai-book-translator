package translator

import (
	"fmt"
	"strings"

	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

func BuildSystemPrompt(sourceLang, targetLang, stylePrompt string) string {
	srcName := model.GetLanguageName(sourceLang)
	tgtName := model.GetLanguageName(targetLang)

	var sb strings.Builder

	sb.WriteString("You are a professional literary translator.\n")
	sb.WriteString(fmt.Sprintf(
		"Your task is to translate text faithfully from %s to %s.\n\n",
		srcName, tgtName,
	))
	sb.WriteString("Rules:\n")
	sb.WriteString("- Output ONLY the translated text.\n")
	sb.WriteString("- Do NOT add commentary, explanations, or notes.\n")
	sb.WriteString("- Do NOT include the original text.\n")
	sb.WriteString("- Preserve the exact meaning of every sentence.\n")
	sb.WriteString("- Do NOT invent or replace objects, locations, or actions.\n")
	sb.WriteString("- Maintain the original paragraph structure.\n")
	sb.WriteString("- Keep character names and proper nouns unchanged.\n")
	sb.WriteString("- Prefer accuracy over creativity.\n")
	sb.WriteString("- If a sentence is unclear, translate it literally rather than guessing.\n")
	sb.WriteString(fmt.Sprintf("- Maintain natural grammar and style in %s.\n", tgtName))

	if stylePrompt != "" {
		sb.WriteString(fmt.Sprintf("\nStyle: %s\n", stylePrompt))
	}

	return sb.String()
}

// BuildUserMessage wraps the source text for translation with faithful translation instructions.
// If genreContext is provided, it will be injected before the "Text:" section.
func BuildUserMessage(sourceLang, targetLang, text, genreContext string) string {
	srcName := model.GetLanguageName(sourceLang)
	tgtName := model.GetLanguageName(targetLang)
	
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf(
		"Translate the following text from %s into %s.\n",
		srcName, tgtName,
	))
	sb.WriteString("Translate faithfully and preserve the meaning of every sentence. ")
	sb.WriteString("Do not summarize or invent new details.\n\n")
	
	if genreContext != "" {
		sb.WriteString(genreContext)
		sb.WriteString("\n\n")
	}
	
	sb.WriteString("Text:\n")
	sb.WriteString(text)
	
	return sb.String()
}

func StripThinkingTags(text string) string {
	for {
		start := strings.Index(text, "<think>")
		if start == -1 {
			break
		}
		end := strings.Index(text, "</think>")
		if end == -1 {
			text = text[:start]
			break
		}
		text = text[:start] + text[end+len("</think>"):]
	}
	return strings.TrimSpace(text)
}
