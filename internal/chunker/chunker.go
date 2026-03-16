package chunker

import (
	"strings"
	"unicode/utf8"

	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

const DefaultMaxSize = 500

type Chunker struct {
	Strategy string
	MaxSize  int
}

func New(strategy string, maxSize int) *Chunker {
	if strategy == "" {
		strategy = model.ChunkStrategyParagraph
	}
	if maxSize <= 0 {
		maxSize = DefaultMaxSize
	}
	return &Chunker{Strategy: strategy, MaxSize: maxSize}
}

func (c *Chunker) Chunk(text string) []string {
	switch c.Strategy {
	case model.ChunkStrategySentences:
		return c.bySentences(text)
	case model.ChunkStrategyTokens:
		return c.byTokenCount(text)
	default:
		return c.byParagraph(text)
	}
}

func (c *Chunker) byParagraph(text string) []string {
	paragraphs := splitParagraphs(text)
	if len(paragraphs) == 0 {
		return nil
	}

	var chunks []string
	var current strings.Builder

	for _, p := range paragraphs {
		pLen := approxTokens(p)

		if pLen > c.MaxSize {
			if current.Len() > 0 {
				chunks = append(chunks, strings.TrimSpace(current.String()))
				current.Reset()
			}
			for _, sub := range c.splitLongText(p) {
				chunks = append(chunks, sub)
			}
			continue
		}

		currentLen := approxTokens(current.String())
		if currentLen+pLen > c.MaxSize && current.Len() > 0 {
			chunks = append(chunks, strings.TrimSpace(current.String()))
			current.Reset()
		}

		if current.Len() > 0 {
			current.WriteString("\n\n")
		}
		current.WriteString(p)
	}

	if current.Len() > 0 {
		chunks = append(chunks, strings.TrimSpace(current.String()))
	}

	return chunks
}

func (c *Chunker) bySentences(text string) []string {
	sentences := splitSentences(text)
	if len(sentences) == 0 {
		return nil
	}

	var chunks []string
	var current strings.Builder

	for _, s := range sentences {
		sLen := approxTokens(s)
		currentLen := approxTokens(current.String())

		if currentLen+sLen > c.MaxSize && current.Len() > 0 {
			chunks = append(chunks, strings.TrimSpace(current.String()))
			current.Reset()
		}

		if current.Len() > 0 {
			current.WriteString(" ")
		}
		current.WriteString(s)
	}

	if current.Len() > 0 {
		chunks = append(chunks, strings.TrimSpace(current.String()))
	}

	return chunks
}

func (c *Chunker) byTokenCount(text string) []string {
	words := strings.Fields(text)
	if len(words) == 0 {
		return nil
	}

	var chunks []string
	var current strings.Builder
	count := 0

	for _, w := range words {
		if count >= c.MaxSize && current.Len() > 0 {
			chunks = append(chunks, strings.TrimSpace(current.String()))
			current.Reset()
			count = 0
		}
		if current.Len() > 0 {
			current.WriteString(" ")
		}
		current.WriteString(w)
		count++
	}

	if current.Len() > 0 {
		chunks = append(chunks, strings.TrimSpace(current.String()))
	}

	return chunks
}

func (c *Chunker) splitLongText(text string) []string {
	words := strings.Fields(text)
	var chunks []string
	var current strings.Builder
	count := 0

	for _, w := range words {
		if count >= c.MaxSize && current.Len() > 0 {
			chunks = append(chunks, strings.TrimSpace(current.String()))
			current.Reset()
			count = 0
		}
		if current.Len() > 0 {
			current.WriteString(" ")
		}
		current.WriteString(w)
		count++
	}

	if current.Len() > 0 {
		chunks = append(chunks, strings.TrimSpace(current.String()))
	}

	return chunks
}

func splitParagraphs(text string) []string {
	raw := strings.Split(text, "\n")
	var paragraphs []string
	var current strings.Builder

	for _, line := range raw {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			if current.Len() > 0 {
				paragraphs = append(paragraphs, strings.TrimSpace(current.String()))
				current.Reset()
			}
			continue
		}
		if current.Len() > 0 {
			current.WriteString(" ")
		}
		current.WriteString(trimmed)
	}

	if current.Len() > 0 {
		paragraphs = append(paragraphs, strings.TrimSpace(current.String()))
	}

	return paragraphs
}

func splitSentences(text string) []string {
	var sentences []string
	var current strings.Builder

	for i := 0; i < len(text); {
		r, size := utf8.DecodeRuneInString(text[i:])
		current.WriteRune(r)
		i += size

		if r == '.' || r == '!' || r == '?' {
			if i < len(text) {
				next, _ := utf8.DecodeRuneInString(text[i:])
				if next == ' ' || next == '\n' || next == '\r' {
					s := strings.TrimSpace(current.String())
					if s != "" {
						sentences = append(sentences, s)
					}
					current.Reset()
				}
			}
		}
	}

	if current.Len() > 0 {
		s := strings.TrimSpace(current.String())
		if s != "" {
			sentences = append(sentences, s)
		}
	}

	return sentences
}

// Rough approximation: ~1 token per 4 characters for English.
func approxTokens(s string) int {
	n := utf8.RuneCountInString(s)
	return (n + 3) / 4
}
