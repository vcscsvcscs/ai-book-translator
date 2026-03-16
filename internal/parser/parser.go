package parser

import (
	"fmt"
	"path/filepath"
	"strings"
)

type ParsedChapter struct {
	Title   string
	Content string
	Ref     string
}

type Parser interface {
	Parse(filePath string) ([]ParsedChapter, error)
}

func ForFile(filePath string) (Parser, error) {
	ext := strings.ToLower(filepath.Ext(filePath))
	switch ext {
	case ".epub":
		return &EPUBParser{}, nil
	case ".pdf":
		return &PDFParser{}, nil
	case ".md", ".markdown":
		return &MarkdownParser{}, nil
	default:
		return nil, fmt.Errorf("unsupported file format: %s", ext)
	}
}
