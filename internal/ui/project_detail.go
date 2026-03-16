package ui

import (
	"fmt"
	"sync"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/widget"
	"github.com/vcscsvcscs/ai-book-translator/internal/exporter"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/translator"
)

func buildProjectDetail(p *model.Project) fyne.CanvasObject {
	completed, total := p.Progress()
	failed := p.FailedChunks()
	pct := 0.0
	if total > 0 {
		pct = float64(completed) / float64(total)
	}

	title := widget.NewLabel(p.Name)
	title.TextStyle = fyne.TextStyle{Bold: true}

	providerInfo := p.Provider
	if p.ProviderURL != "" {
		providerInfo += " @ " + p.ProviderURL
	}
	statusLabel := widget.NewLabel(fmt.Sprintf(
		"Status: %s | %s→%s | %s | %s",
		p.Status, p.SourceLang, p.TargetLang, p.ModelPath, providerInfo,
	))

	progressBar := widget.NewProgressBar()
	progressBar.SetValue(pct)

	progressLabel := widget.NewLabel(fmt.Sprintf(
		"%d/%d completed, %d failed", completed, total, failed,
	))

	logEntry := widget.NewMultiLineEntry()
	logEntry.SetMinRowsVisible(6)
	logEntry.Disable()
	logEntry.SetPlaceHolder("Translation log will appear here…")

	var mu sync.Mutex
	var translating bool

	translateBtn := widget.NewButton("Translate All", nil)

	runTranslation := func(chapterIndices []int) {
		mu.Lock()
		if translating {
			mu.Unlock()
			return
		}
		translating = true
		mu.Unlock()

		translateBtn.SetText("Translating…")
		translateBtn.Disable()

		t := translator.New(appStore)

		cb := func(e translator.ProgressEvent) {
			fyne.Do(func() {
				switch e.EventType {
				case translator.EventChunkStart:
					appendLog(logEntry, fmt.Sprintf("[ch %d / chunk %d] translating…", e.ChapterIndex, e.ChunkIndex))
				case translator.EventChunkDone:
					progressBar.SetValue(e.TotalProgress)
					c, tot := p.Progress()
					progressLabel.SetText(fmt.Sprintf("%d/%d completed, %d failed", c, tot, p.FailedChunks()))
					appendLog(logEntry, fmt.Sprintf("  chunk done (%.0f%%)", e.TotalProgress*100))
				case translator.EventChunkFailed:
					appendLog(logEntry, fmt.Sprintf("  FAILED: %v", e.Error))
				case translator.EventChapterDone:
					appendLog(logEntry, fmt.Sprintf("[chapter %d complete]", e.ChapterIndex))
				case translator.EventAllDone:
					appendLog(logEntry, fmt.Sprintf("Translation finished (%.0f%%)", e.TotalProgress*100))
				}
			})
		}

		go func() {
			if len(chapterIndices) > 0 {
				t.TranslateChapters(p, chapterIndices, cb)
			} else {
				t.TranslateProject(p, cb)
			}

			mu.Lock()
			translating = false
			mu.Unlock()

			fyne.Do(func() {
				translateBtn.SetText("Translate All")
				translateBtn.Enable()
				reloaded, err := appStore.Load(p.ID)
				if err == nil {
					showProjectDetail(reloaded)
				}
			})
		}()
	}

	translateBtn.OnTapped = func() { runTranslation(nil) }

	translateSelectedBtn := widget.NewButton("Translate Selected…", func() {
		showChapterSelectDialog(p, runTranslation)
	})

	changeModelBtn := widget.NewButton("Change Model…", func() {
		showChangeModelDialog(p)
	})

	rechunkBtn := widget.NewButton("Rechunk…", func() {
		showRechunkDialog(p)
	})

	var actionRow fyne.CanvasObject
	if completed > 0 {
		exportBtn := widget.NewButton("Export…", func() {
			showExportDialog(p)
		})
		actionRow = container.NewHBox(translateBtn, translateSelectedBtn, changeModelBtn, rechunkBtn, exportBtn)
	} else {
		actionRow = container.NewHBox(translateBtn, translateSelectedBtn, changeModelBtn, rechunkBtn)
	}

	chapterList := buildChapterList(p)

	header := container.NewVBox(
		title,
		statusLabel,
		progressBar,
		progressLabel,
		actionRow,
	)

	logScroll := container.NewVScroll(logEntry)
	logScroll.SetMinSize(fyne.NewSize(0, 130))

	return container.NewBorder(header, logScroll, nil, nil, chapterList)
}

func buildChapterList(p *model.Project) fyne.CanvasObject {
	list := widget.NewList(
		func() int { return len(p.Chapters) },
		func() fyne.CanvasObject {
			return container.NewHBox(
				widget.NewLabel("Chapter title"),
				widget.NewLabel("0/0"),
			)
		},
		func(id widget.ListItemID, obj fyne.CanvasObject) {
			if id >= len(p.Chapters) {
				return
			}
			ch := &p.Chapters[id]
			box := obj.(*fyne.Container)
			box.Objects[0].(*widget.Label).SetText(ch.Title)
			cc, ct := ch.Progress()
			box.Objects[1].(*widget.Label).SetText(fmt.Sprintf("%d/%d", cc, ct))
		},
	)

	list.OnSelected = func(id widget.ListItemID) {
		if id >= len(p.Chapters) {
			return
		}
		showChapterView(p, id)
	}

	return list
}

func appendLog(entry *widget.Entry, text string) {
	current := entry.Text
	if current != "" {
		current += "\n"
	}
	entry.SetText(current + text)
}

func showExportDialog(p *model.Project) {
	formatSelect := widget.NewSelect(
		[]string{model.FormatEPUB, model.FormatPDF, model.FormatMarkdown},
		nil,
	)
	if p.ExportFormat != "" {
		formatSelect.SetSelected(p.ExportFormat)
	} else {
		formatSelect.SetSelected(model.FormatEPUB)
	}

	outputEntry := widget.NewEntry()
	outputEntry.SetPlaceHolder("Output path (auto-generated if empty)")

	items := []*widget.FormItem{
		{Text: "Format", Widget: formatSelect},
		{Text: "Output Path", Widget: outputEntry},
	}

	dialog.ShowForm("Export Project", "Export", "Cancel", items, func(ok bool) {
		if !ok {
			return
		}

		format := formatSelect.Selected
		output := outputEntry.Text
		if output == "" {
			output = exporter.DefaultOutputPath(p, format)
		}

		exp, err := exporter.ForFormat(format)
		if err != nil {
			dialog.ShowError(err, mainWindow)
			return
		}

		if err := exp.Export(p, output); err != nil {
			dialog.ShowError(err, mainWindow)
			return
		}

		// Persist the chosen export format as the new default
		p.ExportFormat = format
		_ = appStore.Save(p)

		dialog.ShowInformation("Export Complete", fmt.Sprintf("Exported to:\n%s", output), mainWindow)
	}, mainWindow)
}

func showChangeModelDialog(p *model.Project) {
	providerSelect := widget.NewSelect(
		[]string{"ollama", "dlgo-http", "dlgo"},
		nil,
	)
	providerSelect.SetSelected(p.Provider)

	providerURLEntry := widget.NewEntry()
	providerURLEntry.SetText(p.ProviderURL)
	providerURLEntry.SetPlaceHolder("e.g. http://localhost:11434")

	modelEntry := widget.NewEntry()
	modelEntry.SetText(p.ModelPath)
	modelEntry.SetPlaceHolder("Model name or path")

	// For Ollama: replace the text entry with a select populated from the server.
	modelSelect := widget.NewSelect(nil, func(s string) {
		modelEntry.SetText(s)
	})

	fetchBtn := widget.NewButton("Fetch Models", func() {
		url := providerURLEntry.Text
		if url == "" {
			url = translator.DefaultOllamaURL
		}
		models, err := translator.ListOllamaModels(url)
		if err != nil {
			dialog.ShowError(err, mainWindow)
			return
		}
		modelSelect.Options = models
		modelSelect.Refresh()
		if len(models) > 0 {
			// Pre-select current model if present, else first
			for _, m := range models {
				if m == p.ModelPath {
					modelSelect.SetSelected(m)
					return
				}
			}
			modelSelect.SetSelected(models[0])
		}
	})

	// Trigger fetch immediately if provider is ollama
	ollamaRow := container.NewBorder(nil, nil, nil, fetchBtn, modelSelect)

	modelWidget := widget.NewLabel("") // placeholder, swapped below
	_ = modelWidget

	providerSelect.OnChanged = func(s string) {
		// nothing extra needed; form items are fixed after creation
	}

	// Build form items — show ollama picker or plain entry depending on provider
	var modelFormWidget fyne.CanvasObject
	if p.Provider == model.ProviderOllama {
		modelFormWidget = ollamaRow
		// auto-fetch on open
		go func() {
			url := p.ProviderURL
			if url == "" {
				url = translator.DefaultOllamaURL
			}
			models, err := translator.ListOllamaModels(url)
			if err != nil {
				return
			}
			fyne.Do(func() {
				modelSelect.Options = models
				modelSelect.Refresh()
				for _, m := range models {
					if m == p.ModelPath {
						modelSelect.SetSelected(m)
						return
					}
				}
				if len(models) > 0 {
					modelSelect.SetSelected(models[0])
				}
			})
		}()
	} else {
		modelFormWidget = modelEntry
	}

	items := []*widget.FormItem{
		{Text: "Provider", Widget: providerSelect},
		{Text: "Provider URL", Widget: providerURLEntry},
		{Text: "Model", Widget: modelFormWidget},
	}

	dialog.ShowForm("Change Model", "Save", "Cancel", items, func(ok bool) {
		if !ok {
			return
		}
		p.Provider = providerSelect.Selected
		p.ProviderURL = providerURLEntry.Text
		// Use select value for ollama, entry for others
		if p.Provider == model.ProviderOllama && modelSelect.Selected != "" {
			p.ModelPath = modelSelect.Selected
		} else {
			p.ModelPath = modelEntry.Text
		}
		if err := appStore.Save(p); err != nil {
			dialog.ShowError(err, mainWindow)
			return
		}
		showProjectDetail(p)
	}, mainWindow)
}

func showChapterSelectDialog(p *model.Project, onConfirm func([]int)) {
	checks := make([]*widget.Check, len(p.Chapters))
	items := make([]fyne.CanvasObject, len(p.Chapters))
	for i, ch := range p.Chapters {
		cc, ct := ch.Progress()
		label := fmt.Sprintf("[%d] %s (%d/%d)", ch.Index, ch.Title, cc, ct)
		c := widget.NewCheck(label, nil)
		checks[i] = c
		items[i] = c
	}

	content := container.NewVScroll(container.NewVBox(items...))
	content.SetMinSize(fyne.NewSize(400, 300))

	d := dialog.NewCustomConfirm("Select Chapters", "Translate", "Cancel", content, func(ok bool) {
		if !ok {
			return
		}
		var selected []int
		for i, c := range checks {
			if c.Checked {
				selected = append(selected, i)
			}
		}
		if len(selected) == 0 {
			return
		}
		onConfirm(selected)
	}, mainWindow)
	d.Show()
}

func showRechunkDialog(p *model.Project) {
	strategySelect := widget.NewSelect(
		[]string{"paragraph", "sentences", "tokens"},
		nil,
	)
	strategySelect.SetSelected(p.ChunkStrategy)

	chunkSizeEntry := widget.NewEntry()
	chunkSizeEntry.SetText(fmt.Sprintf("%d", p.ChunkMaxSize))

	completed, _ := p.Progress()
	warningLabel := widget.NewLabel("")
	if completed > 0 {
		warningLabel.SetText("Warning: completed translations will be preserved where source text matches, but unmatched chunks will reset to pending.")
		warningLabel.Wrapping = fyne.TextWrapWord
	}

	items := []*widget.FormItem{
		{Text: "Chunk Strategy", Widget: strategySelect},
		{Text: "Max Chunk Size", Widget: chunkSizeEntry},
	}
	if completed > 0 {
		items = append(items, &widget.FormItem{Text: "", Widget: warningLabel})
	}

	dialog.ShowForm("Rechunk Project", "Rechunk", "Cancel", items, func(ok bool) {
		if !ok {
			return
		}
		maxSize := 0
		fmt.Sscanf(chunkSizeEntry.Text, "%d", &maxSize)

		t := translator.New(appStore)
		if err := t.Rechunk(p, strategySelect.Selected, maxSize); err != nil {
			dialog.ShowError(err, mainWindow)
			return
		}

		reloaded, err := appStore.Load(p.ID)
		if err != nil {
			dialog.ShowError(err, mainWindow)
			return
		}
		showProjectDetail(reloaded)
	}, mainWindow)
}
