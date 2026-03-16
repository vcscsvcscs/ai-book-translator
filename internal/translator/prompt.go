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

	sb.WriteString(fmt.Sprintf(
		"You are a professional literary translator specializing in %s to %s translation.\n",
		srcName, tgtName,
	))
	sb.WriteString(fmt.Sprintf(
		"Your sole task is to output the %s translation of whatever text the user provides — nothing else.\n\n",
		tgtName,
	))
	sb.WriteString("Rules:\n")
	sb.WriteString("- Output ONLY the translated text. No preamble, no commentary, no notes, no explanations.\n")
	sb.WriteString("- Do NOT include the source text in your response.\n")
	sb.WriteString("- Do NOT translate the word-for-word; produce natural, fluent literary prose.\n")
	sb.WriteString(fmt.Sprintf("- Use correct %s grammar and natural sentence structure.\n", tgtName))
	sb.WriteString("- Preserve all paragraph breaks exactly as in the source.\n")
	sb.WriteString("- Keep proper nouns (character names, place names) unchanged.\n")
	sb.WriteString("- Do not continue, summarize, or add to the story.\n")

	if stylePrompt != "" {
		sb.WriteString(fmt.Sprintf("\nStyle: %s\n", stylePrompt))
	}

	return sb.String()
}

// BuildUserMessage wraps the source text for translation.
func BuildUserMessage(sourceLang, targetLang, text string) string {
	tgtName := model.GetLanguageName(targetLang)
	return fmt.Sprintf("Translate the following text into %s. Output only the translation, nothing else.\n\n%s",
		tgtName, text)
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
