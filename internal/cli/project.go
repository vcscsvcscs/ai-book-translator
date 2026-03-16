package cli

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"text/tabwriter"

	"github.com/spf13/cobra"
	"github.com/vcscsvcscs/ai-book-translator/internal/chunker"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/parser"
)

func init() {
	rootCmd.AddCommand(projectCmd)
	projectCmd.AddCommand(projectCreateCmd)
	projectCmd.AddCommand(projectListCmd)
	projectCmd.AddCommand(projectShowCmd)
	projectCmd.AddCommand(projectDeleteCmd)

	f := projectCreateCmd.Flags()
	f.String("name", "", "Project name")
	f.String("input", "", "Input file path (epub, pdf, or md)")
	f.String("model", "", "Model name (Ollama) or path to .gguf file (dlgo)")
	f.String("from", "", "Source language")
	f.String("to", "", "Target language")
	f.String("style", "", "Extra style prompt for translation")
	f.Int("chunk-size", chunker.DefaultMaxSize, "Max chunk size (approx tokens)")
	f.String("chunk-strategy", model.ChunkStrategyParagraph, "Chunking strategy: paragraph, sentences, tokens")
	f.String("export-format", model.FormatEPUB, "Default export format: epub, pdf, md")
	f.Float32("temperature", 0.3, "Sampling temperature")
	f.Int("max-tokens", 2048, "Max tokens per response")
	f.String("thinking", model.ThinkingDisabled, "Thinking mode: disabled, enabled, budget")
	f.Int("thinking-budget", 0, "Thinking token budget (with --thinking=budget)")
	f.String("provider", model.ProviderOllama, "Inference provider: ollama, dlgo-http, dlgo")
	f.String("provider-url", "", "Provider server URL (default: http://localhost:11434 for ollama)")
}

var projectCmd = &cobra.Command{
	Use:   "project",
	Short: "Manage translation projects",
}

var projectCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a new translation project",
	RunE: func(cmd *cobra.Command, args []string) error {
		name, _ := cmd.Flags().GetString("name")
		input, _ := cmd.Flags().GetString("input")
		modelPath, _ := cmd.Flags().GetString("model")
		fromLang, _ := cmd.Flags().GetString("from")
		toLang, _ := cmd.Flags().GetString("to")
		style, _ := cmd.Flags().GetString("style")
		chunkSize, _ := cmd.Flags().GetInt("chunk-size")
		chunkStrategy, _ := cmd.Flags().GetString("chunk-strategy")
		exportFormat, _ := cmd.Flags().GetString("export-format")
		temperature, _ := cmd.Flags().GetFloat32("temperature")
		maxTokens, _ := cmd.Flags().GetInt("max-tokens")
		thinking, _ := cmd.Flags().GetString("thinking")
		thinkingBudget, _ := cmd.Flags().GetInt("thinking-budget")
		provider, _ := cmd.Flags().GetString("provider")
		providerURL, _ := cmd.Flags().GetString("provider-url")

		if input == "" {
			return fmt.Errorf("--input is required")
		}
		if modelPath == "" {
			return fmt.Errorf("--model is required")
		}
		if fromLang == "" || toLang == "" {
			return fmt.Errorf("--from and --to are required")
		}

		if provider == "" {
			provider = cfg.Provider
		}
		if providerURL == "" {
			switch provider {
			case model.ProviderOllama:
				providerURL = cfg.OllamaURL
			case model.ProviderDlgoHTTP:
				providerURL = cfg.DlgoURL
			}
		}

		if name == "" {
			base := filepath.Base(input)
			name = strings.TrimSuffix(base, filepath.Ext(base)) + " translation"
		}

		fmt.Printf("Parsing %s...\n", input)

		p, err := parser.ForFile(input)
		if err != nil {
			return err
		}

		chapters, err := p.Parse(input)
		if err != nil {
			return fmt.Errorf("parse input: %w", err)
		}

		c := chunker.New(chunkStrategy, chunkSize)

		var projChapters []model.Chapter
		for i, ch := range chapters {
			chunks := c.Chunk(ch.Content)
			var modelChunks []model.Chunk
			for j, text := range chunks {
				modelChunks = append(modelChunks, model.Chunk{
					Index:      j,
					SourceText: text,
					Status:     model.ChunkPending,
				})
			}
			projChapters = append(projChapters, model.Chapter{
				Index:     i,
				Title:     ch.Title,
				SourceRef: ch.Ref,
				Chunks:    modelChunks,
			})
		}

		ext := strings.ToLower(filepath.Ext(input))
		sourceFormat := strings.TrimPrefix(ext, ".")
		if sourceFormat == "markdown" {
			sourceFormat = "md"
		}

		proj := &model.Project{
			Name:          name,
			SourceFile:    input,
			SourceFormat:  sourceFormat,
			Provider:      provider,
			ProviderURL:   providerURL,
			ModelPath:     modelPath,
			SourceLang:    fromLang,
			TargetLang:    toLang,
			StylePrompt:   style,
			ChunkStrategy: chunkStrategy,
			ChunkMaxSize:  chunkSize,
			ModelParams: model.ModelParams{
				Temperature:    temperature,
				MaxTokens:      maxTokens,
				TopK:           40,
				TopP:           0.9,
				ThinkingMode:   thinking,
				ThinkingBudget: thinkingBudget,
			},
			ExportFormat: exportFormat,
			Chapters:     projChapters,
		}

		if err := appStore.Create(proj); err != nil {
			return fmt.Errorf("create project: %w", err)
		}

		// Copy source file into project directory
		projDir := appStore.ProjectDir(proj.ID)
		destPath := filepath.Join(projDir, filepath.Base(input))
		if err := copyFile(input, destPath); err != nil {
			fmt.Fprintf(os.Stderr, "Warning: could not copy source file: %v\n", err)
		} else {
			proj.SourceFile = destPath
			_ = appStore.Save(proj)
		}

		totalChunks := 0
		for _, ch := range proj.Chapters {
			totalChunks += len(ch.Chunks)
		}

		fmt.Printf("Created project: %s\n", proj.ID)
		fmt.Printf("  Name:     %s\n", proj.Name)
		fmt.Printf("  Chapters: %d\n", len(proj.Chapters))
		fmt.Printf("  Chunks:   %d\n", totalChunks)
		fmt.Printf("  Model:    %s\n", proj.ModelPath)
		fmt.Printf("  %s -> %s\n", proj.SourceLang, proj.TargetLang)

		return nil
	},
}

var projectListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all projects",
	RunE: func(cmd *cobra.Command, args []string) error {
		projects, err := appStore.List()
		if err != nil {
			return err
		}

		if len(projects) == 0 {
			fmt.Println("No projects found.")
			return nil
		}

		w := tabwriter.NewWriter(os.Stdout, 0, 4, 2, ' ', 0)
		fmt.Fprintln(w, "ID\tNAME\tSTATUS\tPROGRESS\tLANGS\tUPDATED")
		for _, p := range projects {
			completed, total := p.Progress()
			pct := 0.0
			if total > 0 {
				pct = float64(completed) / float64(total) * 100
			}
			fmt.Fprintf(w, "%s\t%s\t%s\t%d/%d (%.0f%%)\t%s->%s\t%s\n",
				shortID(p.ID), p.Name, p.Status,
				completed, total, pct,
				p.SourceLang, p.TargetLang,
				p.UpdatedAt.Format("2006-01-02 15:04"),
			)
		}
		return w.Flush()
	},
}

var projectShowCmd = &cobra.Command{
	Use:   "show [id]",
	Short: "Show project details",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		p, err := resolveProject(args[0])
		if err != nil {
			return err
		}

		completed, total := p.Progress()
		failed := p.FailedChunks()

		fmt.Printf("Project: %s\n", p.ID)
		fmt.Printf("  Name:          %s\n", p.Name)
		fmt.Printf("  Status:        %s\n", p.Status)
		fmt.Printf("  Source:        %s (%s)\n", filepath.Base(p.SourceFile), p.SourceFormat)
		fmt.Printf("  Languages:     %s -> %s\n", p.SourceLang, p.TargetLang)
		fmt.Printf("  Provider:      %s", p.Provider)
		if p.ProviderURL != "" {
			fmt.Printf(" (%s)", p.ProviderURL)
		}
		fmt.Println()
		fmt.Printf("  Model:         %s\n", p.ModelPath)
		fmt.Printf("  Thinking:      %s", p.ModelParams.ThinkingMode)
		if p.ModelParams.ThinkingMode == model.ThinkingBudget {
			fmt.Printf(" (budget: %d)", p.ModelParams.ThinkingBudget)
		}
		fmt.Println()
		fmt.Printf("  Chunk:         %s (max %d)\n", p.ChunkStrategy, p.ChunkMaxSize)
		fmt.Printf("  Progress:      %d/%d completed", completed, total)
		if failed > 0 {
			fmt.Printf(", %d failed", failed)
		}
		fmt.Println()
		fmt.Printf("  Export format: %s\n", p.ExportFormat)
		fmt.Printf("  Created:       %s\n", p.CreatedAt.Format("2006-01-02 15:04:05"))
		fmt.Printf("  Updated:       %s\n", p.UpdatedAt.Format("2006-01-02 15:04:05"))

		fmt.Println("\n  Chapters:")
		for _, ch := range p.Chapters {
			cc, ct := ch.Progress()
			fmt.Printf("    [%d] %s - %d/%d chunks\n", ch.Index, ch.Title, cc, ct)
		}

		return nil
	},
}

var projectDeleteCmd = &cobra.Command{
	Use:   "delete [id]",
	Short: "Delete a project",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		p, err := resolveProject(args[0])
		if err != nil {
			return err
		}
		if err := appStore.Delete(p.ID); err != nil {
			return err
		}
		fmt.Printf("Deleted project %s (%s)\n", shortID(p.ID), p.Name)
		return nil
	},
}

func resolveProject(idOrPrefix string) (*model.Project, error) {
	p, err := appStore.Load(idOrPrefix)
	if err == nil {
		return p, nil
	}

	projects, listErr := appStore.List()
	if listErr != nil {
		return nil, err
	}

	var matches []*model.Project
	for _, proj := range projects {
		if strings.HasPrefix(proj.ID, idOrPrefix) {
			matches = append(matches, proj)
		}
	}

	switch len(matches) {
	case 0:
		return nil, fmt.Errorf("project not found: %s", idOrPrefix)
	case 1:
		return matches[0], nil
	default:
		return nil, fmt.Errorf("ambiguous project ID prefix %q matches %d projects", idOrPrefix, len(matches))
	}
}

func shortID(id string) string {
	if len(id) > 8 {
		return id[:8]
	}
	return id
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()

	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, in)
	return err
}
