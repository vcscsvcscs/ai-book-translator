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
	translateBtn.OnTapped = func() {
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

		go func() {
			t.TranslateProject(p, func(e translator.ProgressEvent) {
				switch e.EventType {
				case translator.EventChunkStart:
					appendLog(logEntry, fmt.Sprintf("[ch %d / chunk %d] translating…", e.ChapterIndex, e.ChunkIndex))

				case translator.EventToken:
					// token streaming — could update a streaming label here

				case translator.EventChunkDone:
					progressBar.SetValue(e.TotalProgress)
					c, tot := p.Progress()
					progressLabel.SetText(fmt.Sprintf(
						"%d/%d completed, %d failed", c, tot, p.FailedChunks(),
					))
					appendLog(logEntry, fmt.Sprintf("  chunk done (%.0f%%)", e.TotalProgress*100))

				case translator.EventChunkFailed:
					appendLog(logEntry, fmt.Sprintf("  FAILED: %v", e.Error))

				case translator.EventChapterDone:
					appendLog(logEntry, fmt.Sprintf("[chapter %d complete]", e.ChapterIndex))

				case translator.EventAllDone:
					appendLog(logEntry, fmt.Sprintf("Translation finished (%.0f%%)", e.TotalProgress*100))
				}
			})

			mu.Lock()
			translating = false
			mu.Unlock()
			translateBtn.SetText("Translate All")
			translateBtn.Enable()

			reloaded, err := appStore.Load(p.ID)
			if err == nil {
				showProjectDetail(reloaded)
			}
		}()
	}

	// Export button only shown once some translation has been done
	var actionRow fyne.CanvasObject
	if completed > 0 {
		exportBtn := widget.NewButton("Export…", func() {
			showExportDialog(p)
		})
		actionRow = container.NewHBox(translateBtn, exportBtn)
	} else {
		actionRow = container.NewHBox(translateBtn)
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
