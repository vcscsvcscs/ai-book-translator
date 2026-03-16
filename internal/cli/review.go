package cli

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/translator"
)

func init() {
	rootCmd.AddCommand(reviewCmd)

	f := reviewCmd.Flags()
	f.Int("chapter", -1, "Chapter index to review")
	f.Int("chunk", -1, "Chunk index to review (requires --chapter)")
	f.Bool("retranslate", false, "Retranslate the specified chunk")
	f.String("model", "", "Override model for retranslation")
	f.String("thinking", "", "Override thinking mode for retranslation")
	f.Int("thinking-budget", 0, "Override thinking budget for retranslation")
	f.String("server", "", "HTTP server URL for dlgo")
}

var reviewCmd = &cobra.Command{
	Use:   "review [project-id]",
	Short: "Review and optionally retranslate chunks",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		p, err := resolveProject(args[0])
		if err != nil {
			return err
		}

		chapterIdx, _ := cmd.Flags().GetInt("chapter")
		chunkIdx, _ := cmd.Flags().GetInt("chunk")
		retranslate, _ := cmd.Flags().GetBool("retranslate")

		if chapterIdx < 0 {
			return showProjectReview(p)
		}

		if chapterIdx >= len(p.Chapters) {
			return fmt.Errorf("chapter %d out of range (0-%d)", chapterIdx, len(p.Chapters)-1)
		}

		ch := &p.Chapters[chapterIdx]

		if chunkIdx < 0 {
			return showChapterReview(ch)
		}

		if chunkIdx >= len(ch.Chunks) {
			return fmt.Errorf("chunk %d out of range (0-%d)", chunkIdx, len(ch.Chunks)-1)
		}

		chunk := &ch.Chunks[chunkIdx]
		showChunkDetail(chapterIdx, chunkIdx, chunk)

		if retranslate {
			modelPath, _ := cmd.Flags().GetString("model")
			if modelPath == "" {
				modelPath = p.ModelPath
			}

			params := p.ModelParams
			if t, _ := cmd.Flags().GetString("thinking"); t != "" {
				params.ThinkingMode = t
			}
			if b, _ := cmd.Flags().GetInt("thinking-budget"); b > 0 {
				params.ThinkingBudget = b
			}

			server, _ := cmd.Flags().GetString("server")
			var t *translator.Translator
			if server != "" {
				t = translator.NewWithHTTP(appStore, server)
			} else {
				t = translator.New(appStore)
			}

			fmt.Printf("\nRetranslating chunk %d with model %s...\n", chunkIdx, modelPath)
			cb := cliProgressCallback()
			if err := t.RetranslateChunk(p, chapterIdx, chunkIdx, modelPath, params, cb); err != nil {
				return err
			}

			p, _ = appStore.Load(p.ID)
			chunk = &p.Chapters[chapterIdx].Chunks[chunkIdx]
			fmt.Println("\nNew translation:")
			fmt.Println(chunk.TranslatedText)
		}

		return nil
	},
}

func showProjectReview(p *model.Project) error {
	fmt.Printf("Project: %s (%s)\n\n", p.Name, p.Status)
	for _, ch := range p.Chapters {
		cc, ct := ch.Progress()
		statusCounts := make(map[string]int)
		for _, c := range ch.Chunks {
			statusCounts[c.Status]++
		}
		fmt.Printf("[%d] %s - %d/%d done", ch.Index, ch.Title, cc, ct)
		if n := statusCounts[model.ChunkFailed]; n > 0 {
			fmt.Printf(", %d failed", n)
		}
		fmt.Println()
	}
	return nil
}

func showChapterReview(ch *model.Chapter) error {
	fmt.Printf("Chapter %d: %s\n\n", ch.Index, ch.Title)
	for _, c := range ch.Chunks {
		status := statusIcon(c.Status)
		preview := truncate(c.TranslatedText, 60)
		if preview == "" {
			preview = truncate(c.SourceText, 60)
			preview = "(source) " + preview
		}
		fmt.Printf("  %s [%d] %s\n", status, c.Index, preview)
	}
	return nil
}

func showChunkDetail(chapterIdx, chunkIdx int, c *model.Chunk) {
	fmt.Printf("Chapter %d, Chunk %d [%s]\n", chapterIdx, chunkIdx, c.Status)
	if c.ModelUsed != "" {
		fmt.Printf("  Model: %s | Attempts: %d\n", c.ModelUsed, c.Attempts)
	}
	if c.ErrorMessage != "" {
		fmt.Printf("  Error: %s\n", c.ErrorMessage)
	}
	fmt.Println("\n--- Source ---")
	fmt.Println(c.SourceText)
	if c.TranslatedText != "" {
		fmt.Println("\n--- Translation ---")
		fmt.Println(c.TranslatedText)
	}
}

func statusIcon(status string) string {
	switch status {
	case model.ChunkCompleted:
		return "[OK]"
	case model.ChunkFailed:
		return "[FAIL]"
	case model.ChunkRevised:
		return "[REV]"
	case model.ChunkTranslating:
		return "[...]"
	default:
		return "[  ]"
	}
}

func truncate(s string, maxLen int) string {
	s = strings.ReplaceAll(s, "\n", " ")
	s = strings.TrimSpace(s)
	if len(s) > maxLen {
		return s[:maxLen-3] + "..."
	}
	return s
}
