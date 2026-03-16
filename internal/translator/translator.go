package translator

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/store"
)

type Translator struct {
	store      *store.Store
	backends   map[string]LLMBackend
	backendsMu sync.Mutex
}

func New(s *store.Store) *Translator {
	return &Translator{
		store:    s,
		backends: make(map[string]LLMBackend),
	}
}

// getBackend returns (or lazily creates) a cached backend keyed by provider+URL+model.
func (t *Translator) getBackend(provider, providerURL, modelPath string) (LLMBackend, error) {
	key := provider + "|" + providerURL + "|" + modelPath

	t.backendsMu.Lock()
	defer t.backendsMu.Unlock()

	if b, ok := t.backends[key]; ok {
		return b, nil
	}

	var b LLMBackend
	var err error

	switch provider {
	case model.ProviderOllama:
		b = NewOllamaBackend(providerURL, modelPath)
	case model.ProviderDlgoHTTP:
		b = NewHTTPBackend(providerURL, modelPath)
	default: // model.ProviderDlgo
		absPath, _ := filepath.Abs(modelPath)
		b, err = NewDlgoBackend(absPath)
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

			err := t.translateChunk(context.Background(), p, ci, ki, p.Provider, p.ProviderURL, p.ModelPath, p.ModelParams, onProgress, completed, total)
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

// TranslateChapters translates only the specified chapter indices.
func (t *Translator) TranslateChapters(p *model.Project, chapterIndices []int, onProgress ProgressCallback) error {
	p.Status = model.StatusTranslating
	_ = t.store.Save(p)

	completed, total := p.Progress()

	// Build a set for fast lookup
	selected := make(map[int]bool, len(chapterIndices))
	for _, idx := range chapterIndices {
		selected[idx] = true
	}

	for ci := range p.Chapters {
		if !selected[ci] {
			continue
		}
		ch := &p.Chapters[ci]
		for ki := range ch.Chunks {
			chunk := &ch.Chunks[ki]
			if chunk.Status == model.ChunkCompleted || chunk.Status == model.ChunkRevised {
				continue
			}
			err := t.translateChunk(context.Background(), p, ci, ki, p.Provider, p.ProviderURL, p.ModelPath, p.ModelParams, onProgress, completed, total)
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

	p.Status = model.StatusPaused
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
		err := t.translateChunk(context.Background(), p, chapterIdx, ki, p.Provider, p.ProviderURL, p.ModelPath, p.ModelParams, onProgress, completed, total)
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
	return t.translateChunk(context.Background(), p, chapterIdx, chunkIdx, p.Provider, p.ProviderURL, p.ModelPath, p.ModelParams, onProgress, completed, total)
}

// RetranslateChunk retranslates a specific chunk, optionally overriding model and params.
// Pass empty strings for provider/providerURL/modelPath to inherit from the project.
func (t *Translator) RetranslateChunk(
	ctx context.Context,
	p *model.Project,
	chapterIdx, chunkIdx int,
	provider, providerURL, modelPath string,
	params model.ModelParams,
	onProgress ProgressCallback,
) error {
	if chapterIdx < 0 || chapterIdx >= len(p.Chapters) {
		return fmt.Errorf("chapter index %d out of range", chapterIdx)
	}
	ch := &p.Chapters[chapterIdx]
	if chunkIdx < 0 || chunkIdx >= len(ch.Chunks) {
		return fmt.Errorf("chunk index %d out of range", chunkIdx)
	}

	if provider == "" {
		provider = p.Provider
	}
	if providerURL == "" {
		providerURL = p.ProviderURL
	}
	if modelPath == "" {
		modelPath = p.ModelPath
	}

	ch.Chunks[chunkIdx].Status = model.ChunkPending
	ch.Chunks[chunkIdx].TranslatedText = ""
	ch.Chunks[chunkIdx].ErrorMessage = ""

	completed, total := p.Progress()
	return t.translateChunk(ctx, p, chapterIdx, chunkIdx, provider, providerURL, modelPath, params, onProgress, completed, total)
}

func (t *Translator) translateChunk(
	ctx context.Context,
	p *model.Project,
	chapterIdx, chunkIdx int,
	provider, providerURL, modelPath string,
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

	backend, err := t.getBackend(provider, providerURL, modelPath)
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

	systemPrompt := BuildSystemPrompt(p.SourceLang, p.TargetLang, p.StylePrompt)

	var result strings.Builder
	tokenCount := 0
	startTime := time.Now()
	inThink := false

	opts := LLMOptions{
		MaxTokens:         computeMaxOutputTokens(len(chunk.SourceText), p.MaxContextTokens),
		Temperature:       applyDefault(params.Temperature, 0.2),
		TopK:              applyDefaultInt(params.TopK, 40),
		TopP:              applyDefault(params.TopP, 0.9),
		MinP:              params.MinP,
		PresencePenalty:   params.PresencePenalty,
		RepetitionPenalty: applyDefault(params.RepetitionPenalty, 1.1),
		ThinkingMode:      params.ThinkingMode,
		Stop:              []string{"\n\nText:", "<|im_end|>"},
		Seed:              42,
	}

	userMsg := BuildUserMessage(p.SourceLang, p.TargetLang, chunk.SourceText, p.GenreContext)
	err = backend.ChatStream(ctx, systemPrompt, userMsg, func(token string) {
		result.WriteString(token)
		tokenCount++

		// Recompute think state from the full buffer each token.
		// This is simple and correct regardless of how the model tokenises the tags.
		combined := result.String()
		openIdx := strings.LastIndex(combined, "<think>")
		closeIdx := strings.LastIndex(combined, "</think>")
		wasThinking := inThink
		inThink = openIdx != -1 && (closeIdx == -1 || closeIdx < openIdx)

		// Skip emitting the tag tokens themselves so they don't pollute either panel.
		trimmed := strings.TrimRight(token, " \t")
		if trimmed == "<think>" || trimmed == "</think>" {
			return
		}

		// If we just crossed out of a think block, don't emit the closing tag fragment.
		if wasThinking && !inThink {
			// strip any trailing </think> from the token before emitting
			token = strings.TrimSuffix(token, "</think>")
			if token == "" {
				return
			}
		}

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
				IsThinking:   inThink,
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

	translated := StripThinkingTags(result.String())

	displayModel := modelPath
	if provider == model.ProviderOllama || provider == model.ProviderDlgoHTTP {
		displayModel = modelPath
	} else {
		displayModel = filepath.Base(modelPath)
	}

	chunk.TranslatedText = translated
	chunk.Status = model.ChunkCompleted
	chunk.ModelUsed = displayModel
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

// applyDefault returns defaultValue if value is zero, otherwise returns value.
func applyDefault(value, defaultValue float32) float32 {
	if value == 0 {
		return defaultValue
	}
	return value
}

// applyDefaultInt returns defaultValue if value is zero, otherwise returns value.
func applyDefaultInt(value, defaultValue int) int {
	if value == 0 {
		return defaultValue
	}
	return value
}

// computeMaxOutputTokens calculates the maximum output tokens based on chunk size and context window.
// It reserves 1500 tokens for prompts and overhead, ensuring the total stays within maxContext.
func computeMaxOutputTokens(chunkTokens int, maxContext int) int {
	const reserved = 1500 // For system prompt, user prompt, and overhead
	
	if maxContext == 0 {
		maxContext = 32000 // Default context size
	}
	
	available := maxContext - chunkTokens - reserved
	if available < 512 {
		return 512 // Minimum safe output size
	}
	
	return available
}
