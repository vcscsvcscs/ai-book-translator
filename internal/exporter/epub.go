package exporter

import (
	"fmt"
	"strings"

	"github.com/go-shiori/go-epub"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

type EPUBExporter struct{}

func (e *EPUBExporter) Export(p *model.Project, outputPath string) error {
	book, err := epub.NewEpub(p.Name)
	if err != nil {
		return fmt.Errorf("create epub: %w", err)
	}

	book.SetLang(p.TargetLang)
	book.SetAuthor("AI Book Translator")

	for _, ch := range p.Chapters {
		var sb strings.Builder
		for _, c := range ch.Chunks {
			text := c.TranslatedText
			if text == "" {
				text = c.SourceText
			}
			paragraphs := strings.Split(text, "\n")
			for _, para := range paragraphs {
				para = strings.TrimSpace(para)
				if para != "" {
					sb.WriteString("<p>")
					sb.WriteString(para)
					sb.WriteString("</p>\n")
				}
			}
		}

		_, err := book.AddSection(sb.String(), ch.Title, "", "")
		if err != nil {
			return fmt.Errorf("add section %s: %w", ch.Title, err)
		}
	}

	if err := book.Write(outputPath); err != nil {
		return fmt.Errorf("write epub: %w", err)
	}

	return nil
}
