package cli

import (
	"fmt"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"github.com/vcscsvcscs/ai-book-translator/internal/translator"
)

func init() {
	rootCmd.AddCommand(translateCmd)

	f := translateCmd.Flags()
	f.Int("chapter", -1, "Translate only this chapter index")
	f.Int("chunk", -1, "Translate only this chunk index (requires --chapter)")
}

var translateCmd = &cobra.Command{
	Use:   "translate [project-id]",
	Short: "Translate pending chunks in a project",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		p, err := resolveProject(args[0])
		if err != nil {
			return err
		}

		chapterIdx, _ := cmd.Flags().GetInt("chapter")
		chunkIdx, _ := cmd.Flags().GetInt("chunk")

		t := translator.New(appStore)
		cb := cliProgressCallback()

		if chapterIdx >= 0 && chunkIdx >= 0 {
			fmt.Printf("Translating chapter %d, chunk %d...\n", chapterIdx, chunkIdx)
			return t.TranslateSingleChunk(p, chapterIdx, chunkIdx, cb)
		}

		if chapterIdx >= 0 {
			fmt.Printf("Translating chapter %d...\n", chapterIdx)
			return t.TranslateChapter(p, chapterIdx, cb)
		}

		completed, total := p.Progress()
		fmt.Printf("Translating project %q via %s (%d/%d done)...\n", p.Name, p.Provider, completed, total)
		return t.TranslateProject(p, cb)
	},
}

func cliProgressCallback() translator.ProgressCallback {
	var lastLine int
	var tokenBuf strings.Builder
	startTime := time.Now()

	return func(e translator.ProgressEvent) {
		switch e.EventType {
		case translator.EventChunkStart:
			tokenBuf.Reset()
			fmt.Printf("\n[ch %d / chunk %d] translating...\n", e.ChapterIndex, e.ChunkIndex)

		case translator.EventToken:
			tokenBuf.WriteString(e.Token)
			preview := tokenBuf.String()
			if len(preview) > 80 {
				preview = "..." + preview[len(preview)-77:]
			}
			fmt.Printf("\r  %.1f tok/s | %s", e.TokensPerSec, preview)
			lastLine = 1

		case translator.EventChunkDone:
			if lastLine > 0 {
				fmt.Println()
			}
			elapsed := time.Since(startTime)
			fmt.Printf("  done (%.0f%% total, %s elapsed)\n",
				e.TotalProgress*100, elapsed.Round(time.Second))
			lastLine = 0

		case translator.EventChunkFailed:
			if lastLine > 0 {
				fmt.Println()
			}
			fmt.Printf("  FAILED: %v\n", e.Error)
			lastLine = 0

		case translator.EventChapterDone:
			fmt.Printf("[chapter %d complete] %.0f%% total\n", e.ChapterIndex, e.TotalProgress*100)

		case translator.EventAllDone:
			fmt.Printf("\nTranslation finished. %.0f%% complete.\n", e.TotalProgress*100)
		}
	}
}
