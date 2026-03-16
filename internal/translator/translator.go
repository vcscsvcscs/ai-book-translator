package translator

import (
	"fmt"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/store"
)

type BackendType string

const (
	BackendDlgo BackendType = "dlgo"
	BackendHTTP BackendType = "http"
)

type Translator struct {
	store      *store.Store
	backends   map[string]LLMBackend
	backendsMu sync.Mutex
	httpURL    string
	backend    BackendType
}

func New(s *store.Store) *Translator {
	return &Translator{
		store:    s,
		backends: make(map[string]LLMBackend),
		backend:  BackendDlgo,
	}
}

func NewWithHTTP(s *store.Store, serverURL string) *Translator {
	return &Translator{
		store:    s,
		backends: make(map[string]LLMBackend),
		httpURL:  serverURL,
		backend:  BackendHTTP,
	}
}

func (t *Translator) getBackend(modelPath string) (LLMBackend, error) {
	t.backendsMu.Lock()
	defer t.backendsMu.Unlock()

	key := modelPath
	if t.backend == BackendDlgo {
		absPath, err := filepath.Abs(modelPath)
		if err == nil {
			key = absPath
		}
	}

	if b, ok := t.backends[key]; ok {
		return b, nil
	}

	var b LLMBackend
	var err error

	switch t.backend {
	case BackendHTTP:
		b = NewHTTPBackend(t.httpURL, filepath.Base(modelPath))
	default:
		b, err = NewDlgoBackend(key)
		if err != nil {
			return nil, err
		}
	}

	t.backends[key] = b
	return b, nil
}

func (t *Translator) TranslateProject(p *model.Project, onProgress ProgressCallback) error {
	p.Status = model.StatusTranslating
	p.UpdatedAt = time.Now()
	if err := t.store.Save(p); err != nil {
		return err
	}

	completed, total := p.Progress()

	for ci := range p.Chapters {
		for ki := range p.Chapters[ci].Chunks {
			chunk := &p.Chapters[ci].Chunks[ki]
			if chunk.Status == model.ChunkCompleted || chunk.Status == model.ChunkRevised {
				continue
			}

			err := t.translateChunk(p, ci, ki, p.ModelPath, p.ModelParams, onProgress, completed, total)
			if err == nil {
				completed++
			}
		}

		if onProgress != nil {
			onProgress(ProgressEvent{
				ProjectID:     p.ID,
				ChapterIndex:  ci,
				EventType:     EventChapterDone,
				TotalProgress: safeDiv(float64(completed), float64(total)),
			})
		}
	}

	allDone := true
	for ci := range p.Chapters {
		for ki := range p.Chapters[ci].Chunks {
			s := p.Chapters[ci].Chunks[ki].Status
			if s != model.ChunkCompleted && s != model.ChunkRevised {
				allDone = false
				break
			}
		}
		if !allDone {
			break
		}
	}

	if allDone {
		p.Status = model.StatusCompleted
	} else {
		p.Status = model.StatusPaused
	}
	p.UpdatedAt = time.Now()
	_ = t.store.Save(p)

	if onProgress != nil {
		onProgress(ProgressEvent{
			ProjectID:     p.ID,
			EventType:     EventAllDone,
			TotalProgress: safeDiv(float64(completed), float64(total)),
		})
	}

	return nil
}

func (t *Translator) TranslateChapter(p *model.Project, chapterIdx int, onProgress ProgressCallback) error {
	if chapterIdx < 0 || chapterIdx >= len(p.Chapters) {
		return fmt.Errorf("chapter index %d out of range", chapterIdx)
	}

	p.Status = model.StatusTranslating
	_ = t.store.Save(p)

	completed, total := p.Progress()

	ch := &p.Chapters[chapterIdx]
	for ki := range ch.Chunks {
		chunk := &ch.Chunks[ki]
		if chunk.Status == model.ChunkCompleted || chunk.Status == model.ChunkRevised {
			continue
		}
		err := t.translateChunk(p, chapterIdx, ki, p.ModelPath, p.ModelParams, onProgress, completed, total)
		if err == nil {
			completed++
		}
	}

	return nil
}

func (t *Translator) TranslateSingleChunk(p *model.Project, chapterIdx, chunkIdx int, onProgress ProgressCallback) error {
	if chapterIdx < 0 || chapterIdx >= len(p.Chapters) {
		return fmt.Errorf("chapter index %d out of range", chapterIdx)
	}
	ch := &p.Chapters[chapterIdx]
	if chunkIdx < 0 || chunkIdx >= len(ch.Chunks) {
		return fmt.Errorf("chunk index %d out of range", chunkIdx)
	}

	completed, total := p.Progress()
	return t.translateChunk(p, chapterIdx, chunkIdx, p.ModelPath, p.ModelParams, onProgress, completed, total)
}

func (t *Translator) RetranslateChunk(p *model.Project, chapterIdx, chunkIdx int, modelPath string, params model.ModelParams, onProgress ProgressCallback) error {
	if chapterIdx < 0 || chapterIdx >= len(p.Chapters) {
		return fmt.Errorf("chapter index %d out of range", chapterIdx)
	}
	ch := &p.Chapters[chapterIdx]
	if chunkIdx < 0 || chunkIdx >= len(ch.Chunks) {
		return fmt.Errorf("chunk index %d out of range", chunkIdx)
	}

	ch.Chunks[chunkIdx].Status = model.ChunkPending
	ch.Chunks[chunkIdx].TranslatedText = ""
	ch.Chunks[chunkIdx].ErrorMessage = ""

	completed, total := p.Progress()
	return t.translateChunk(p, chapterIdx, chunkIdx, modelPath, params, onProgress, completed, total)
}

func (t *Translator) translateChunk(
	p *model.Project,
	chapterIdx, chunkIdx int,
	modelPath string,
	params model.ModelParams,
	onProgress ProgressCallback,
	completed, total int,
) error {
	chunk := &p.Chapters[chapterIdx].Chunks[chunkIdx]
	chunk.Status = model.ChunkTranslating
	chunk.Attempts++
	_ = t.store.Save(p)

	if onProgress != nil {
		onProgress(ProgressEvent{
			ProjectID:     p.ID,
			ChapterIndex:  chapterIdx,
			ChunkIndex:    chunkIdx,
			EventType:     EventChunkStart,
			TotalProgress: safeDiv(float64(completed), float64(total)),
		})
	}

	backend, err := t.getBackend(modelPath)
	if err != nil {
		chunk.Status = model.ChunkFailed
		chunk.ErrorMessage = err.Error()
		_ = t.store.Save(p)
		if onProgress != nil {
			onProgress(ProgressEvent{
				ProjectID:    p.ID,
				ChapterIndex: chapterIdx,
				ChunkIndex:   chunkIdx,
				EventType:    EventChunkFailed,
				Error:        err,
			})
		}
		return err
	}

	systemPrompt := BuildSystemPrompt(p.SourceLang, p.TargetLang, p.StylePrompt, params)

	var result strings.Builder
	tokenCount := 0
	startTime := time.Now()

	opts := LLMOptions{
		MaxTokens:   params.MaxTokens,
		Temperature: params.Temperature,
		TopK:        params.TopK,
		TopP:        params.TopP,
	}

	err = backend.ChatStream(systemPrompt, chunk.SourceText, func(token string) {
		result.WriteString(token)
		tokenCount++

		if onProgress != nil {
			elapsed := time.Since(startTime).Seconds()
			tokPerSec := 0.0
			if elapsed > 0 {
				tokPerSec = float64(tokenCount) / elapsed
			}

			onProgress(ProgressEvent{
				ProjectID:    p.ID,
				ChapterIndex: chapterIdx,
				ChunkIndex:   chunkIdx,
				EventType:    EventToken,
				Token:        token,
				TokensPerSec: tokPerSec,
			})
		}
	}, opts)

	if err != nil {
		chunk.Status = model.ChunkFailed
		chunk.ErrorMessage = err.Error()
		chunk.TranslatedAt = time.Now()
		_ = t.store.Save(p)

		if onProgress != nil {
			onProgress(ProgressEvent{
				ProjectID:    p.ID,
				ChapterIndex: chapterIdx,
				ChunkIndex:   chunkIdx,
				EventType:    EventChunkFailed,
				Error:        err,
			})
		}
		return err
	}

	translated := result.String()
	if params.ThinkingMode != model.ThinkingDisabled {
		translated = StripThinkingTags(translated)
	}

	chunk.TranslatedText = translated
	chunk.Status = model.ChunkCompleted
	chunk.ModelUsed = filepath.Base(modelPath)
	chunk.ErrorMessage = ""
	chunk.TranslatedAt = time.Now()
	_ = t.store.Save(p)

	if onProgress != nil {
		onProgress(ProgressEvent{
			ProjectID:     p.ID,
			ChapterIndex:  chapterIdx,
			ChunkIndex:    chunkIdx,
			EventType:     EventChunkDone,
			TotalProgress: safeDiv(float64(completed+1), float64(total)),
		})
	}

	return nil
}

func safeDiv(a, b float64) float64 {
	if b == 0 {
		return 0
	}
	return a / b
}
