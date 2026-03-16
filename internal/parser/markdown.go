package parser

import (
	"fmt"
	"os"
	"regexp"
	"strings"
)

type MarkdownParser struct{}

var headingRe = regexp.MustCompile(`(?m)^(#{1,3})\s+(.+)$`)

func (p *MarkdownParser) Parse(filePath string) ([]ParsedChapter, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("read markdown: %w", err)
	}

	content := string(data)
	if strings.TrimSpace(content) == "" {
		return nil, fmt.Errorf("markdown file is empty")
	}

	matches := headingRe.FindAllStringIndex(content, -1)
	if len(matches) == 0 {
		return []ParsedChapter{{
			Title:   "Document",
			Content: strings.TrimSpace(content),
			Ref:     filePath,
		}}, nil
	}

	var chapters []ParsedChapter
	for i, loc := range matches {
		heading := headingRe.FindString(content[loc[0]:loc[1]])
		title := strings.TrimSpace(strings.TrimLeft(heading, "#"))

		var body string
		if i+1 < len(matches) {
			body = content[loc[1]:matches[i+1][0]]
		} else {
			body = content[loc[1]:]
		}

		body = strings.TrimSpace(body)
		if body == "" {
			continue
		}

		chapters = append(chapters, ParsedChapter{
			Title:   title,
			Content: body,
			Ref:     fmt.Sprintf("heading-%d", i),
		})
	}

	if len(chapters) == 0 {
		return []ParsedChapter{{
			Title:   "Document",
			Content: strings.TrimSpace(content),
			Ref:     filePath,
		}}, nil
	}

	return chapters, nil
}
