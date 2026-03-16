package cli

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/vcscsvcscs/ai-book-translator/internal/exporter"
)

func init() {
	rootCmd.AddCommand(exportCmd)

	exportCmd.Flags().String("format", "", "Export format: epub, pdf, md (defaults to project setting)")
	exportCmd.Flags().String("output", "", "Output file path (auto-generated if not set)")
}

var exportCmd = &cobra.Command{
	Use:   "export [project-id]",
	Short: "Export a translated project",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		p, err := resolveProject(args[0])
		if err != nil {
			return err
		}

		format, _ := cmd.Flags().GetString("format")
		output, _ := cmd.Flags().GetString("output")

		if format == "" {
			format = p.ExportFormat
		}

		exp, err := exporter.ForFormat(format)
		if err != nil {
			return err
		}

		if output == "" {
			output = exporter.DefaultOutputPath(p, format)
		}

		fmt.Printf("Exporting to %s...\n", output)
		if err := exp.Export(p, output); err != nil {
			return fmt.Errorf("export: %w", err)
		}

		fmt.Printf("Exported to %s\n", output)
		return nil
	},
}
