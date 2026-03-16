package cli

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/vcscsvcscs/ai-book-translator/internal/config"
	"github.com/vcscsvcscs/ai-book-translator/internal/store"
)

var (
	cfg     *config.Config
	appStore *store.Store
)

var rootCmd = &cobra.Command{
	Use:   "abt",
	Short: "AI Book Translator - translate books using local LLMs",
	Long:  "A tool for translating books (EPUB, PDF, Markdown) using local GGUF language models via dlgo.",
	PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
		c, err := config.Load()
		if err != nil {
			return fmt.Errorf("load config: %w", err)
		}
		cfg = c
		appStore = store.New(cfg.DataDir)
		return nil
	},
}

func Execute() error {
	return rootCmd.Execute()
}
