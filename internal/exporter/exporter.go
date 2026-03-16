package exporter

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

type Exporter interface {
	Export(project *model.Project, outputPath string) error
}

func ForFormat(format string) (Exporter, error) {
	switch strings.ToLower(format) {
	case model.FormatEPUB:
		return &EPUBExporter{}, nil
	case model.FormatPDF:
		return &PDFExporter{}, nil
	case model.FormatMarkdown, "markdown":
		return &MarkdownExporter{}, nil
	default:
		return nil, fmt.Errorf("unsupported export format: %s", format)
	}
}

func DefaultOutputPath(p *model.Project, format string) string {
	base := strings.TrimSuffix(filepath.Base(p.SourceFile), filepath.Ext(p.SourceFile))
	name := fmt.Sprintf("%s_%s.%s", base, p.TargetLang, format)
	return name
}

func gatherTranslatedText(p *model.Project) string {
	var sb strings.Builder
	for _, ch := range p.Chapters {
		sb.WriteString("# ")
		sb.WriteString(ch.Title)
		sb.WriteString("\n\n")
		for _, c := range ch.Chunks {
			text := c.TranslatedText
			if text == "" {
				text = c.SourceText
			}
			sb.WriteString(text)
			sb.WriteString("\n\n")
		}
	}
	return sb.String()
}
