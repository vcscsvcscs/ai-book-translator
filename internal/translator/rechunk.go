package translator

import (
	"fmt"

	"github.com/vcscsvcscs/ai-book-translator/internal/chunker"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/parser"
)

// Rechunk re-parses the project's source file and re-chunks all chapters using
// the project's current chunk strategy and max size.
// Completed/revised translations are preserved by matching source text.
// strategy and maxSize are optional overrides; pass "" / 0 to keep project values.
func (t *Translator) Rechunk(p *model.Project, strategy string, maxSize int) error {
	if strategy == "" {
		strategy = p.ChunkStrategy
	}
	if maxSize <= 0 {
		maxSize = p.ChunkMaxSize
	}

	par, err := parser.ForFile(p.SourceFile)
	if err != nil {
		return fmt.Errorf("rechunk: get parser: %w", err)
	}

	parsed, err := par.Parse(p.SourceFile)
	if err != nil {
		return fmt.Errorf("rechunk: parse source: %w", err)
	}

	c := chunker.New(strategy, maxSize)

	// Build a lookup of existing completed translations keyed by source text.
	done := make(map[string]model.Chunk)
	for _, ch := range p.Chapters {
		for _, ck := range ch.Chunks {
			if ck.Status == model.ChunkCompleted || ck.Status == model.ChunkRevised {
				done[ck.SourceText] = ck
			}
		}
	}

	var newChapters []model.Chapter
	for i, pc := range parsed {
		texts := c.Chunk(pc.Content)
		var chunks []model.Chunk
		for j, text := range texts {
			ck := model.Chunk{
				Index:      j,
				SourceText: text,
				Status:     model.ChunkPending,
			}
			// Restore completed translation if source text matches.
			if prev, ok := done[text]; ok {
				ck.TranslatedText = prev.TranslatedText
				ck.Status = prev.Status
				ck.ModelUsed = prev.ModelUsed
				ck.Attempts = prev.Attempts
				ck.TranslatedAt = prev.TranslatedAt
			}
			chunks = append(chunks, ck)
		}

		title := pc.Title
		if i < len(p.Chapters) && p.Chapters[i].Title != "" {
			title = p.Chapters[i].Title
		}

		newChapters = append(newChapters, model.Chapter{
			Index:     i,
			Title:     title,
			SourceRef: pc.Ref,
			Chunks:    chunks,
		})
	}

	p.Chapters = newChapters
	p.ChunkStrategy = strategy
	p.ChunkMaxSize = maxSize
	if p.Status == model.StatusCompleted {
		p.Status = model.StatusPaused
	}

	return t.store.Save(p)
}
