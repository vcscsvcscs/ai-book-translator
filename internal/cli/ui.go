package cli

import (
	"github.com/spf13/cobra"
	"github.com/vcscsvcscs/ai-book-translator/internal/ui"
)

func init() {
	rootCmd.AddCommand(uiCmd)
	uiCmd.Flags().String("server", "", "HTTP server URL for dlgo (e.g. http://localhost:8080)")
}

var uiCmd = &cobra.Command{
	Use:   "ui",
	Short: "Launch the graphical user interface",
	RunE: func(cmd *cobra.Command, args []string) error {
		server, _ := cmd.Flags().GetString("server")
		ui.Run(cfg, appStore, server)
		return nil
	},
}
