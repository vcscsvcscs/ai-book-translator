package parser

import (
	"fmt"
	"strings"

	"github.com/ledongthuc/pdf"
)

type PDFParser struct{}

func (p *PDFParser) Parse(filePath string) ([]ParsedChapter, error) {
	f, r, err := pdf.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("open pdf: %w", err)
	}
	defer f.Close()

	numPages := r.NumPage()
	if numPages == 0 {
		return nil, fmt.Errorf("pdf has no pages")
	}

	var chapters []ParsedChapter
	var currentText strings.Builder
	chapterIdx := 1
	pagesPerChapter := 10

	for i := 1; i <= numPages; i++ {
		page := r.Page(i)
		if page.V.IsNull() {
			continue
		}

		text, err := page.GetPlainText(nil)
		if err != nil {
			continue
		}

		trimmed := strings.TrimSpace(text)
		if trimmed == "" {
			continue
		}

		if currentText.Len() > 0 {
			currentText.WriteString("\n")
		}
		currentText.WriteString(trimmed)

		if i%pagesPerChapter == 0 || i == numPages {
			content := strings.TrimSpace(currentText.String())
			if content != "" {
				chapters = append(chapters, ParsedChapter{
					Title:   fmt.Sprintf("Section %d", chapterIdx),
					Content: content,
					Ref:     fmt.Sprintf("pages-%d-%d", i-pagesPerChapter+1, i),
				})
				chapterIdx++
			}
			currentText.Reset()
		}
	}

	if len(chapters) == 0 {
		return nil, fmt.Errorf("no text content found in pdf")
	}

	return chapters, nil
}
