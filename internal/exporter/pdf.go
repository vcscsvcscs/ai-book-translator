package exporter

import (
	"os"
	"strings"

	"github.com/jung-kurt/gofpdf"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

type PDFExporter struct{}

func (e *PDFExporter) Export(p *model.Project, outputPath string) error {
	pdf := gofpdf.New("P", "mm", "A4", "")
	pdf.SetAutoPageBreak(true, 20)

	fontName := "Helvetica"
	if fontPath := findFont(); fontPath != "" {
		pdf.AddUTF8Font("CustomFont", "", fontPath)
		pdf.AddUTF8Font("CustomFont", "B", fontPath)
		fontName = "CustomFont"
	}

	for _, ch := range p.Chapters {
		pdf.AddPage()

		pdf.SetFont(fontName, "B", 16)
		pdf.MultiCell(0, 10, ch.Title, "", "L", false)
		pdf.Ln(5)

		pdf.SetFont(fontName, "", 11)
		for _, c := range ch.Chunks {
			text := c.TranslatedText
			if text == "" {
				text = c.SourceText
			}
			paragraphs := strings.Split(text, "\n")
			for _, para := range paragraphs {
				para = strings.TrimSpace(para)
				if para != "" {
					pdf.MultiCell(0, 6, para, "", "L", false)
					pdf.Ln(3)
				}
			}
		}
	}

	return pdf.OutputFileAndClose(outputPath)
}

func findFont() string {
	paths := []string{
		"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
		"/usr/share/fonts/TTF/DejaVuSans.ttf",
		"/System/Library/Fonts/Supplemental/Arial.ttf",
		"/Library/Fonts/Arial.ttf",
	}
	for _, p := range paths {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	return ""
}
