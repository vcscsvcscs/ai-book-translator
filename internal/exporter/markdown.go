package exporter

import (
	"os"

	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

type MarkdownExporter struct{}

func (e *MarkdownExporter) Export(p *model.Project, outputPath string) error {
	content := gatherTranslatedText(p)
	return os.WriteFile(outputPath, []byte(content), 0o644)
}
