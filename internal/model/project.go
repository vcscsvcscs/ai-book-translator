package model

import "time"

const (
	StatusCreated     = "created"
	StatusTranslating = "translating"
	StatusPaused      = "paused"
	StatusCompleted   = "completed"

	ChunkPending     = "pending"
	ChunkTranslating = "translating"
	ChunkCompleted   = "completed"
	ChunkFailed      = "failed"
	ChunkRevised     = "revised"
)

type Project struct {
	ID            string      `json:"id"`
	Name          string      `json:"name"`
	SourceFile    string      `json:"source_file"`
	SourceFormat  string      `json:"source_format"`
	// Provider is the inference backend: "ollama", "dlgo-http", or "dlgo".
	Provider    string `json:"provider"`
	// ProviderURL is the server URL for ollama or dlgo-http backends.
	ProviderURL string `json:"provider_url"`
	// ModelPath is the model name (Ollama) or file path (dlgo/dlgo-http).
	ModelPath     string      `json:"model_path"`
	SourceLang    string      `json:"source_lang"`
	TargetLang    string      `json:"target_lang"`
	StylePrompt   string      `json:"style_prompt"`
	ChunkStrategy string      `json:"chunk_strategy"`
	ChunkMaxSize  int         `json:"chunk_max_size"`
	ModelParams   ModelParams `json:"model_params"`
	ExportFormat  string      `json:"export_format"`
	Status        string      `json:"status"`
	Chapters      []Chapter   `json:"chapters"`
	CreatedAt     time.Time   `json:"created_at"`
	UpdatedAt     time.Time   `json:"updated_at"`
}

type Chapter struct {
	Index     int     `json:"index"`
	Title     string  `json:"title"`
	SourceRef string  `json:"source_ref"`
	Chunks    []Chunk `json:"chunks"`
}

type Chunk struct {
	Index          int       `json:"index"`
	SourceText     string    `json:"source_text"`
	TranslatedText string    `json:"translated_text"`
	Status         string    `json:"status"`
	ModelUsed      string    `json:"model_used"`
	ErrorMessage   string    `json:"error_message"`
	Attempts       int       `json:"attempts"`
	TranslatedAt   time.Time `json:"translated_at"`
}

func (p *Project) Progress() (completed, total int) {
	for i := range p.Chapters {
		for j := range p.Chapters[i].Chunks {
			total++
			if p.Chapters[i].Chunks[j].Status == ChunkCompleted || p.Chapters[i].Chunks[j].Status == ChunkRevised {
				completed++
			}
		}
	}
	return
}

func (p *Project) FailedChunks() int {
	count := 0
	for i := range p.Chapters {
		for j := range p.Chapters[i].Chunks {
			if p.Chapters[i].Chunks[j].Status == ChunkFailed {
				count++
			}
		}
	}
	return count
}

func (c *Chapter) Progress() (completed, total int) {
	for i := range c.Chunks {
		total++
		if c.Chunks[i].Status == ChunkCompleted || c.Chunks[i].Status == ChunkRevised {
			completed++
		}
	}
	return
}
