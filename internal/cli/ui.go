package cli

import (
	"github.com/spf13/cobra"
	"github.com/vcscsvcscs/ai-book-translator/internal/ui"
)

func init() {
	rootCmd.AddCommand(uiCmd)
}

var uiCmd = &cobra.Command{
	Use:   "ui",
	Short: "Launch the graphical user interface",
	RunE: func(cmd *cobra.Command, args []string) error {
		ui.Run(cfg, appStore)
		return nil
	},
}
