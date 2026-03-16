package translator

import (
	"fmt"
	"strings"

	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

func BuildSystemPrompt(sourceLang, targetLang, stylePrompt string, params model.ModelParams) string {
	srcName := model.GetLanguageName(sourceLang)
	tgtName := model.GetLanguageName(targetLang)

	var sb strings.Builder

	sb.WriteString(fmt.Sprintf(
		"You are a professional literary translator. Translate the provided text from %s to %s.\n\n",
		srcName, tgtName,
	))

	sb.WriteString(fmt.Sprintf(
		"Maintain readability and consistency with the source text while making it read naturally in %s. "+
			"Use correct grammar and natural %s sentence structure.\n\n",
		tgtName, tgtName,
	))

	sb.WriteString("IMPORTANT RULES:\n")
	sb.WriteString("- You MUST translate the text exactly — do not continue the story, do not add new content, do not summarize.\n")
	sb.WriteString(fmt.Sprintf("- Output ONLY the complete %s translation of the given text — nothing else.\n", tgtName))
	sb.WriteString("- Do NOT include the original text in your response.\n")
	sb.WriteString("- Do NOT add commentary, notes, or explanations.\n")
	sb.WriteString("- Preserve all paragraph breaks exactly as in the source.\n")
	sb.WriteString("- Keep proper nouns (character names, place names) as-is.\n")

	if stylePrompt != "" {
		sb.WriteString(fmt.Sprintf("\nStyle instructions: %s\n", stylePrompt))
	}

	switch params.ThinkingMode {
	case model.ThinkingEnabled:
		sb.WriteString("\n/think")
	case model.ThinkingBudget:
		if params.ThinkingBudget > 0 {
			sb.WriteString(fmt.Sprintf("\n/think budget=%d", params.ThinkingBudget))
		} else {
			sb.WriteString("\n/think")
		}
	default:
		sb.WriteString("\n/no_think")
	}

	return sb.String()
}

// BuildUserMessage wraps the source text with explicit framing so the model
// cannot mistake the instruction for content to translate.
func BuildUserMessage(sourceLang, targetLang, text string) string {
	tgtName := model.GetLanguageName(targetLang)
	return fmt.Sprintf("Text to translate:\n%s\n\nTranslation in %s:", text, tgtName)
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
