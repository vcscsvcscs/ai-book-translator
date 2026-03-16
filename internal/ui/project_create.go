package ui

import (
	"os"
	"path/filepath"
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/storage"
	"fyne.io/fyne/v2/widget"
	"github.com/vcscsvcscs/ai-book-translator/internal/chunker"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/parser"
)

func showCreateProject(onDone func()) {
	nameEntry := widget.NewEntry()
	nameEntry.SetPlaceHolder("Project name (auto from file if empty)")

	filePathEntry := widget.NewEntry()
	filePathEntry.SetPlaceHolder("Path to EPUB, PDF, or MD file")

	browseBtn := widget.NewButton("Browse...", func() {
		fd := dialog.NewFileOpen(func(reader fyne.URIReadCloser, err error) {
			if err != nil || reader == nil {
				return
			}
			filePathEntry.SetText(reader.URI().Path())
			reader.Close()
		}, mainWindow)
		fd.SetFilter(storage.NewExtensionFileFilter([]string{".epub", ".pdf", ".md", ".markdown"}))
		fd.Show()
	})

	modelEntry := widget.NewEntry()
	modelEntry.SetPlaceHolder("Path to .gguf model file")

	modelBrowseBtn := widget.NewButton("Browse...", func() {
		fd := dialog.NewFileOpen(func(reader fyne.URIReadCloser, err error) {
			if err != nil || reader == nil {
				return
			}
			modelEntry.SetText(reader.URI().Path())
			reader.Close()
		}, mainWindow)
		fd.SetFilter(storage.NewExtensionFileFilter([]string{".gguf", ".ggml", ".bin"}))
		fd.Show()
	})

	models := scanModels()
	modelSelect := widget.NewSelect(models, func(s string) {
		modelEntry.SetText(filepath.Join(appConfig.ModelsDir, s))
	})
	modelSelect.PlaceHolder = "Or select from models dir..."

	sourceLang := widget.NewEntry()
	sourceLang.SetText("en")
	targetLang := widget.NewEntry()
	targetLang.SetText("hu")

	styleEntry := widget.NewMultiLineEntry()
	styleEntry.SetPlaceHolder("Extra style instructions (optional)")
	styleEntry.SetMinRowsVisible(3)

	chunkSizeEntry := widget.NewEntry()
	chunkSizeEntry.SetText("500")

	strategySelect := widget.NewSelect(
		[]string{model.ChunkStrategyParagraph, model.ChunkStrategySentences, model.ChunkStrategyTokens},
		nil,
	)
	strategySelect.SetSelected(model.ChunkStrategyParagraph)

	exportSelect := widget.NewSelect(
		[]string{model.FormatEPUB, model.FormatPDF, model.FormatMarkdown},
		nil,
	)
	exportSelect.SetSelected(model.FormatEPUB)

	thinkingSelect := widget.NewSelect(
		[]string{model.ThinkingDisabled, model.ThinkingEnabled, model.ThinkingBudget},
		nil,
	)
	thinkingSelect.SetSelected(model.ThinkingDisabled)

	thinkingBudgetEntry := widget.NewEntry()
	thinkingBudgetEntry.SetPlaceHolder("Token budget (for budget mode)")

	form := &widget.Form{
		Items: []*widget.FormItem{
			{Text: "Name", Widget: nameEntry},
			{Text: "Input File", Widget: container.NewBorder(nil, nil, nil, browseBtn, filePathEntry)},
			{Text: "Model", Widget: container.NewBorder(nil, nil, nil, modelBrowseBtn, modelEntry)},
			{Text: "Model (dir)", Widget: modelSelect},
			{Text: "Source Lang", Widget: sourceLang},
			{Text: "Target Lang", Widget: targetLang},
			{Text: "Style Prompt", Widget: styleEntry},
			{Text: "Chunk Strategy", Widget: strategySelect},
			{Text: "Chunk Size", Widget: chunkSizeEntry},
			{Text: "Export Format", Widget: exportSelect},
			{Text: "Thinking", Widget: thinkingSelect},
			{Text: "Think Budget", Widget: thinkingBudgetEntry},
		},
		OnSubmit: func() {
			filePath := filePathEntry.Text
			if filePath == "" {
				dialog.ShowError(nil, mainWindow)
				return
			}

			p, err := parser.ForFile(filePath)
			if err != nil {
				dialog.ShowError(err, mainWindow)
				return
			}

			chapters, err := p.Parse(filePath)
			if err != nil {
				dialog.ShowError(err, mainWindow)
				return
			}

			chunkSize := 500
			if v := chunkSizeEntry.Text; v != "" {
				n := 0
				for _, c := range v {
					if c >= '0' && c <= '9' {
						n = n*10 + int(c-'0')
					}
				}
				if n > 0 {
					chunkSize = n
				}
			}

			c := chunker.New(strategySelect.Selected, chunkSize)

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

			name := nameEntry.Text
			if name == "" {
				base := filepath.Base(filePath)
				name = strings.TrimSuffix(base, filepath.Ext(base)) + " translation"
			}

			ext := strings.ToLower(filepath.Ext(filePath))
			sourceFormat := strings.TrimPrefix(ext, ".")
			if sourceFormat == "markdown" {
				sourceFormat = "md"
			}

			thinkBudget := 0
			if v := thinkingBudgetEntry.Text; v != "" {
				for _, c := range v {
					if c >= '0' && c <= '9' {
						thinkBudget = thinkBudget*10 + int(c-'0')
					}
				}
			}

			proj := &model.Project{
				Name:          name,
				SourceFile:    filePath,
				SourceFormat:  sourceFormat,
				ModelPath:     modelEntry.Text,
				SourceLang:    sourceLang.Text,
				TargetLang:    targetLang.Text,
				StylePrompt:   styleEntry.Text,
				ChunkStrategy: strategySelect.Selected,
				ChunkMaxSize:  chunkSize,
				ModelParams: model.ModelParams{
					Temperature:    0.3,
					MaxTokens:      2048,
					TopK:           40,
					TopP:           0.9,
					ThinkingMode:   thinkingSelect.Selected,
					ThinkingBudget: thinkBudget,
				},
				ExportFormat: exportSelect.Selected,
				Chapters:     projChapters,
			}

			if err := appStore.Create(proj); err != nil {
				dialog.ShowError(err, mainWindow)
				return
			}

			if onDone != nil {
				onDone()
			}
			showProjectDetail(proj)
		},
		OnCancel: func() {
			refreshProjectList()
		},
	}

	scroll := container.NewVScroll(form)
	projectList := buildProjectList()
	split := container.NewHSplit(projectList, scroll)
	split.SetOffset(0.3)
	mainWindow.SetContent(split)
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
