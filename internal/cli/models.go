package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"text/tabwriter"

	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(modelsCmd)
	modelsCmd.AddCommand(modelsListCmd)
}

var modelsCmd = &cobra.Command{
	Use:   "models",
	Short: "Manage GGUF models",
}

var modelsListCmd = &cobra.Command{
	Use:   "list",
	Short: "List available GGUF models in the models directory",
	RunE: func(cmd *cobra.Command, args []string) error {
		dir := cfg.ModelsDir
		fmt.Printf("Models directory: %s\n\n", dir)

		entries, err := os.ReadDir(dir)
		if err != nil {
			if os.IsNotExist(err) {
				fmt.Println("No models directory found. Create it or configure models_dir in config.")
				return nil
			}
			return err
		}

		var models []os.DirEntry
		for _, e := range entries {
			if e.IsDir() {
				continue
			}
			ext := filepath.Ext(e.Name())
			if ext == ".gguf" || ext == ".ggml" || ext == ".bin" {
				models = append(models, e)
			}
		}

		if len(models) == 0 {
			fmt.Println("No GGUF models found. Place .gguf files in the models directory.")
			return nil
		}

		w := tabwriter.NewWriter(os.Stdout, 0, 4, 2, ' ', 0)
		fmt.Fprintln(w, "NAME\tSIZE\tPATH")
		for _, m := range models {
			info, err := m.Info()
			if err != nil {
				continue
			}
			size := formatSize(info.Size())
			fmt.Fprintf(w, "%s\t%s\t%s\n", m.Name(), size, filepath.Join(dir, m.Name()))
		}
		return w.Flush()
	},
}

func formatSize(bytes int64) string {
	const (
		mb = 1024 * 1024
		gb = 1024 * 1024 * 1024
	)
	switch {
	case bytes >= gb:
		return fmt.Sprintf("%.1f GB", float64(bytes)/float64(gb))
	case bytes >= mb:
		return fmt.Sprintf("%.1f MB", float64(bytes)/float64(mb))
	default:
		return fmt.Sprintf("%d B", bytes)
	}
}
