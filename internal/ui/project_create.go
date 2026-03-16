package ui

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/storage"
	"fyne.io/fyne/v2/widget"
	"github.com/vcscsvcscs/ai-book-translator/internal/chunker"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/parser"
	"github.com/vcscsvcscs/ai-book-translator/internal/translator"
)

func showCreateProject(onDone func()) {
	// ── Name ────────────────────────────────────────────────────────────────
	nameEntry := widget.NewEntry()
	nameEntry.SetPlaceHolder("Auto-generated from filename if empty")

	// ── Input file ──────────────────────────────────────────────────────────
	filePathEntry := widget.NewEntry()
	filePathEntry.SetPlaceHolder("Path to EPUB, PDF, or Markdown file")
	browseFileBtn := widget.NewButton("Browse…", func() {
		fd := dialog.NewFileOpen(func(rc fyne.URIReadCloser, err error) {
			if err != nil || rc == nil {
				return
			}
			filePathEntry.SetText(rc.URI().Path())
			rc.Close()
		}, mainWindow)
		fd.SetFilter(storage.NewExtensionFileFilter([]string{".epub", ".pdf", ".md", ".markdown"}))
		fd.Show()
	})

	// ── Provider ────────────────────────────────────────────────────────────
	providerSelect := widget.NewSelect(
		[]string{model.ProviderOllama, model.ProviderDlgoHTTP, model.ProviderDlgo},
		nil,
	)
	providerSelect.SetSelected(appConfig.Provider)

	// ── Provider URL ─────────────────────────────────────────────────────────
	providerURLEntry := widget.NewEntry()
	providerURLEntry.SetText(resolveDefaultURL(appConfig.Provider))

	// Update URL hint when provider changes
	providerSelect.OnChanged = func(p string) {
		providerURLEntry.SetText(resolveDefaultURL(p))
	}

	// ── Model ────────────────────────────────────────────────────────────────
	modelEntry := widget.NewEntry()
	modelEntry.SetPlaceHolder("Model name (Ollama) or path to .gguf file (dlgo)")

	// Ollama model selector
	ollamaModelSelect := widget.NewSelect(nil, func(s string) {
		modelEntry.SetText(s)
	})
	ollamaModelSelect.PlaceHolder = "Fetch models first…"

	fetchOllamaBtn := widget.NewButton("Fetch Ollama Models", func() {
		url := providerURLEntry.Text
		if url == "" {
			url = appConfig.OllamaURL
		}
		models, err := translator.ListOllamaModels(url)
		if err != nil {
			dialog.ShowError(err, mainWindow)
			return
		}
		if len(models) == 0 {
			dialog.ShowInformation("No models", "No models found in Ollama. Pull one with:\n  ollama pull qwen3.5:9b", mainWindow)
			return
		}
		ollamaModelSelect.Options = models
		ollamaModelSelect.SetSelected(models[0])
		modelEntry.SetText(models[0])
		ollamaModelSelect.Refresh()
	})

	// Local GGUF file browser for dlgo
	browseModelBtn := widget.NewButton("Browse .gguf…", func() {
		fd := dialog.NewFileOpen(func(rc fyne.URIReadCloser, err error) {
			if err != nil || rc == nil {
				return
			}
			modelEntry.SetText(rc.URI().Path())
			rc.Close()
		}, mainWindow)
		fd.SetFilter(storage.NewExtensionFileFilter([]string{".gguf", ".ggml", ".bin"}))
		fd.Show()
	})

	// Scan local models dir and show in a select
	localModels := scanModels()
	localModelSelect := widget.NewSelect(localModels, func(s string) {
		modelEntry.SetText(filepath.Join(appConfig.ModelsDir, s))
	})
	localModelSelect.PlaceHolder = "Select from models dir…"

	// ── Languages ────────────────────────────────────────────────────────────
	langOptions := model.SortedLanguageOptions()

	sourceLangSelect := widget.NewSelect(langOptions, nil)
	sourceLangSelect.SetSelected("en - English")

	targetLangSelect := widget.NewSelect(langOptions, nil)
	targetLangSelect.SetSelected("hu - Hungarian")

	// ── Style ────────────────────────────────────────────────────────────────
	styleEntry := widget.NewMultiLineEntry()
	styleEntry.SetPlaceHolder("Optional style instructions, e.g. \"Keep informal tone\"")
	styleEntry.SetMinRowsVisible(3)

	// ── Chunking ─────────────────────────────────────────────────────────────
	strategySelect := widget.NewSelect(
		[]string{model.ChunkStrategyParagraph, model.ChunkStrategySentences, model.ChunkStrategyTokens},
		nil,
	)
	strategySelect.SetSelected(model.ChunkStrategyParagraph)

	chunkSizeEntry := widget.NewEntry()
	chunkSizeEntry.SetText("500")

	// ── Model params ─────────────────────────────────────────────────────────
	defaults := model.DefaultModelParams()

	temperatureEntry := widget.NewEntry()
	temperatureEntry.SetText(fmt.Sprintf("%.2f", defaults.Temperature))

	maxTokensEntry := widget.NewEntry()
	maxTokensEntry.SetText(strconv.Itoa(defaults.MaxTokens))

	topKEntry := widget.NewEntry()
	topKEntry.SetText(strconv.Itoa(defaults.TopK))

	topPEntry := widget.NewEntry()
	topPEntry.SetText(fmt.Sprintf("%.2f", defaults.TopP))

	minPEntry := widget.NewEntry()
	minPEntry.SetText(fmt.Sprintf("%.2f", defaults.MinP))

	presencePenaltyEntry := widget.NewEntry()
	presencePenaltyEntry.SetText(fmt.Sprintf("%.2f", defaults.PresencePenalty))

	repetitionPenaltyEntry := widget.NewEntry()
	repetitionPenaltyEntry.SetText(fmt.Sprintf("%.2f", defaults.RepetitionPenalty))

	thinkingSelect := widget.NewSelect(
		[]string{model.ThinkingDisabled, model.ThinkingEnabled, model.ThinkingBudget},
		nil,
	)
	thinkingSelect.SetSelected(model.ThinkingDisabled)

	thinkingBudgetEntry := widget.NewEntry()
	thinkingBudgetEntry.SetPlaceHolder("Token budget (budget mode only)")

	presetSelect := widget.NewSelect([]string{
		"— Qwen3 Non-Thinking (general)",
		"— Qwen3 Thinking (general)",
	}, func(s string) {
		var preset model.ModelParams
		switch s {
		case "— Qwen3 Non-Thinking (general)":
			preset = model.Qwen3PresetNonThinking()
		case "— Qwen3 Thinking (general)":
			preset = model.Qwen3PresetThinking()
		default:
			return
		}
		temperatureEntry.SetText(fmt.Sprintf("%.2f", preset.Temperature))
		maxTokensEntry.SetText(strconv.Itoa(preset.MaxTokens))
		topKEntry.SetText(strconv.Itoa(preset.TopK))
		topPEntry.SetText(fmt.Sprintf("%.2f", preset.TopP))
		minPEntry.SetText(fmt.Sprintf("%.2f", preset.MinP))
		presencePenaltyEntry.SetText(fmt.Sprintf("%.2f", preset.PresencePenalty))
		repetitionPenaltyEntry.SetText(fmt.Sprintf("%.2f", preset.RepetitionPenalty))
		thinkingSelect.SetSelected(preset.ThinkingMode)
	})
	presetSelect.PlaceHolder = "Load preset…"

	// ── Form ─────────────────────────────────────────────────────────────────
	modelBrowseRow := container.NewBorder(nil, nil, nil, browseModelBtn, modelEntry)
	ollamaRow := container.NewBorder(nil, nil, nil, fetchOllamaBtn, ollamaModelSelect)

	form := &widget.Form{
		Items: []*widget.FormItem{
			{Text: "Project Name", Widget: nameEntry},
			{Text: "Input File", Widget: container.NewBorder(nil, nil, nil, browseFileBtn, filePathEntry)},
			{Text: "Provider", Widget: providerSelect},
			{Text: "Provider URL", Widget: providerURLEntry},
			{Text: "Model", Widget: modelBrowseRow},
			{Text: "Ollama Models", Widget: ollamaRow},
			{Text: "Local Models Dir", Widget: localModelSelect},
			{Text: "Source Language", Widget: sourceLangSelect},
			{Text: "Target Language", Widget: targetLangSelect},
			{Text: "Style Prompt", Widget: styleEntry},
			{Text: "Chunk Strategy", Widget: strategySelect},
			{Text: "Chunk Size", Widget: chunkSizeEntry},
			{Text: "Preset", Widget: presetSelect},
			{Text: "Temperature", Widget: temperatureEntry},
			{Text: "Max Tokens", Widget: maxTokensEntry},
			{Text: "Top K", Widget: topKEntry},
			{Text: "Top P", Widget: topPEntry},
			{Text: "Min P", Widget: minPEntry},
			{Text: "Presence Penalty", Widget: presencePenaltyEntry},
			{Text: "Repetition Penalty", Widget: repetitionPenaltyEntry},
			{Text: "Thinking Mode", Widget: thinkingSelect},
			{Text: "Think Budget", Widget: thinkingBudgetEntry},
		},
		OnSubmit: func() {
			if err := createProjectFromForm(
				nameEntry.Text,
				filePathEntry.Text,
				providerSelect.Selected,
				providerURLEntry.Text,
				modelEntry.Text,
				model.CodeFromOption(sourceLangSelect.Selected),
				model.CodeFromOption(targetLangSelect.Selected),
				styleEntry.Text,
				strategySelect.Selected,
				chunkSizeEntry.Text,
				temperatureEntry.Text,
				maxTokensEntry.Text,
				topKEntry.Text,
				topPEntry.Text,
				minPEntry.Text,
				presencePenaltyEntry.Text,
				repetitionPenaltyEntry.Text,
				thinkingSelect.Selected,
				thinkingBudgetEntry.Text,
				onDone,
			); err != nil {
				dialog.ShowError(err, mainWindow)
			}
		},
		OnCancel: func() {
			refreshProjectList()
		},
	}

	scroll := container.NewVScroll(form)
	projectList := buildProjectList()
	split := container.NewHSplit(projectList, scroll)
	split.SetOffset(0.28)
	mainWindow.SetContent(split)
}

func createProjectFromForm(
	name, filePath, provider, providerURL, modelPath,
	sourceLang, targetLang, stylePrompt, strategy,
	chunkSizeStr, temperatureStr, maxTokensStr,
	topKStr, topPStr, minPStr, presencePenaltyStr, repetitionPenaltyStr,
	thinkingMode, thinkingBudgetStr string,
	onDone func(),
) error {
	if filePath == "" {
		return fmt.Errorf("input file is required")
	}
	if modelPath == "" {
		return fmt.Errorf("model is required")
	}

	p, err := parser.ForFile(filePath)
	if err != nil {
		return err
	}
	chapters, err := p.Parse(filePath)
	if err != nil {
		return err
	}

	chunkSize := parseIntOr(chunkSizeStr, chunker.DefaultMaxSize)
	c := chunker.New(strategy, chunkSize)

	var projChapters []model.Chapter
	for i, ch := range chapters {
		chunks := c.Chunk(ch.Content)
		var mc []model.Chunk
		for j, text := range chunks {
			mc = append(mc, model.Chunk{Index: j, SourceText: text, Status: model.ChunkPending})
		}
		projChapters = append(projChapters, model.Chapter{
			Index: i, Title: ch.Title, SourceRef: ch.Ref, Chunks: mc,
		})
	}

	if name == "" {
		base := filepath.Base(filePath)
		name = strings.TrimSuffix(base, filepath.Ext(base)) + " translation"
	}

	ext := strings.ToLower(filepath.Ext(filePath))
	sourceFormat := strings.TrimPrefix(ext, ".")
	if sourceFormat == "markdown" {
		sourceFormat = "md"
	}

	if providerURL == "" {
		providerURL = resolveDefaultURL(provider)
	}

	proj := &model.Project{
		Name:          name,
		SourceFile:    filePath,
		SourceFormat:  sourceFormat,
		Provider:      provider,
		ProviderURL:   providerURL,
		ModelPath:     modelPath,
		SourceLang:    sourceLang,
		TargetLang:    targetLang,
		StylePrompt:   stylePrompt,
		ChunkStrategy: strategy,
		ChunkMaxSize:  chunkSize,
		ModelParams: model.ModelParams{
			Temperature:       parseFloat32Or(temperatureStr, 0.7),
			MaxTokens:         parseIntOr(maxTokensStr, 2048),
			TopK:              parseIntOr(topKStr, 20),
			TopP:              parseFloat32Or(topPStr, 0.8),
			MinP:              parseFloat32Or(minPStr, 0.0),
			PresencePenalty:   parseFloat32Or(presencePenaltyStr, 1.5),
			RepetitionPenalty: parseFloat32Or(repetitionPenaltyStr, 1.0),
			ThinkingMode:      thinkingMode,
			ThinkingBudget:    parseIntOr(thinkingBudgetStr, 0),
		},
		ExportFormat: model.FormatEPUB,
		Chapters:     projChapters,
	}

	if err := appStore.Create(proj); err != nil {
		return err
	}

	if onDone != nil {
		onDone()
	}
	showProjectDetail(proj)
	return nil
}

func resolveDefaultURL(provider string) string {
	switch provider {
	case model.ProviderOllama:
		return appConfig.OllamaURL
	case model.ProviderDlgoHTTP:
		return appConfig.DlgoURL
	default:
		return ""
	}
}

func scanModels() []string {
	entries, err := os.ReadDir(appConfig.ModelsDir)
	if err != nil {
		return nil
	}
	var models []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		ext := filepath.Ext(e.Name())
		if ext == ".gguf" || ext == ".ggml" || ext == ".bin" {
			models = append(models, e.Name())
		}
	}
	return models
}

func parseIntOr(s string, def int) int {
	n := 0
	for _, c := range strings.TrimSpace(s) {
		if c >= '0' && c <= '9' {
			n = n*10 + int(c-'0')
		}
	}
	if n == 0 {
		return def
	}
	return n
}

func parseFloat32Or(s string, def float32) float32 {
	s = strings.TrimSpace(s)
	if s == "" {
		return def
	}
	// Simple decimal parser
	var intPart, fracPart int
	var fracDiv float32 = 1
	seenDot := false
	for _, c := range s {
		if c == '.' {
			seenDot = true
			continue
		}
		if c >= '0' && c <= '9' {
			d := int(c - '0')
			if seenDot {
				fracPart = fracPart*10 + d
				fracDiv *= 10
			} else {
				intPart = intPart*10 + d
			}
		}
	}
	return float32(intPart) + float32(fracPart)/fracDiv
}
