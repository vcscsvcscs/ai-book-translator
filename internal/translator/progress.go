package translator

const (
	EventChunkStart  = "chunk_start"
	EventToken       = "token"
	EventChunkDone   = "chunk_done"
	EventChunkFailed = "chunk_failed"
	EventChapterDone = "chapter_done"
	EventAllDone     = "all_done"
)

type ProgressEvent struct {
	ProjectID     string
	ChapterIndex  int
	ChunkIndex    int
	EventType     string
	Token         string
	TokensPerSec  float64
	ChunkProgress float64
	TotalProgress float64
	Error         error
}

type ProgressCallback func(ProgressEvent)
