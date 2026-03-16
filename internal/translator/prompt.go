package translator

import (
	"fmt"
	"strings"

	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

func BuildSystemPrompt(sourceLang, targetLang, stylePrompt string, params model.ModelParams) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf(
		"You are a professional translator. Translate the following text from %s to %s.\n",
		sourceLang, targetLang,
	))

	if stylePrompt != "" {
		sb.WriteString(stylePrompt)
		sb.WriteString("\n")
	}

	sb.WriteString(`Rules:
- Preserve all formatting, paragraph breaks, and structure
- Do not add explanations or commentary
- Output only the translated text`)

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
