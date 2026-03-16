package ui

import (
	"fmt"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/dialog"
	"fyne.io/fyne/v2/widget"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/translator"
)

func showReviewDialog(p *model.Project, chapterIdx, chunkIdx int) {
	chunk := &p.Chapters[chapterIdx].Chunks[chunkIdx]

	titleLabel := widget.NewLabel(fmt.Sprintf(
		"Chapter %d, Chunk %d  [%s]", chapterIdx, chunkIdx, chunk.Status,
	))
	titleLabel.TextStyle = fyne.TextStyle{Bold: true}

	infoLabel := widget.NewLabel("")
	if chunk.ModelUsed != "" {
		infoLabel.SetText(fmt.Sprintf("Model: %s | Attempts: %d", chunk.ModelUsed, chunk.Attempts))
	}

	sourceEntry := widget.NewMultiLineEntry()
	sourceEntry.SetText(chunk.SourceText)
	sourceEntry.Disable()
	sourceEntry.SetMinRowsVisible(10)

	translatedEntry := widget.NewMultiLineEntry()
	translatedEntry.SetText(chunk.TranslatedText)
	translatedEntry.SetMinRowsVisible(10)
	translatedEntry.SetPlaceHolder("No translation yet")

	saveBtn := widget.NewButton("Save Edit", func() {
		chunk.TranslatedText = translatedEntry.Text
		if chunk.Status == model.ChunkCompleted || chunk.Status == model.ChunkFailed {
			chunk.Status = model.ChunkRevised
		}
		if err := appStore.Save(p); err != nil {
			dialog.ShowError(err, mainWindow)
			return
		}
		dialog.ShowInformation("Saved", "Translation revision saved.", mainWindow)
	})

	// ── Retranslate controls ──────────────────────────────────────────────
	modelOverride := widget.NewEntry()
	modelOverride.SetPlaceHolder(fmt.Sprintf("Default: %s", p.ModelPath))

	thinkingSelect := widget.NewSelect(
		[]string{model.ThinkingDisabled, model.ThinkingEnabled, model.ThinkingBudget},
		nil,
	)
	thinkingSelect.SetSelected(p.ModelParams.ThinkingMode)

	streamingLabel := widget.NewLabel("")

	retranslateBtn := widget.NewButton("Retranslate", func() {
		params := p.ModelParams
		params.ThinkingMode = thinkingSelect.Selected

		modelPath := modelOverride.Text

		t := translator.New(appStore)

		streamingLabel.SetText("Translating…")
		translatedEntry.SetText("")

		go func() {
			err := t.RetranslateChunk(
				p, chapterIdx, chunkIdx,
				"", "", modelPath,
				params,
				func(e translator.ProgressEvent) {
					if e.EventType == translator.EventToken {
						translatedEntry.SetText(translatedEntry.Text + e.Token)
					}
					if e.EventType == translator.EventChunkDone || e.EventType == translator.EventChunkFailed {
						streamingLabel.SetText("")
					}
				},
			)
			if err != nil {
				dialog.ShowError(err, mainWindow)
				streamingLabel.SetText("")
				return
			}

			reloaded, loadErr := appStore.Load(p.ID)
			if loadErr == nil {
				showReviewDialog(reloaded, chapterIdx, chunkIdx)
			}
		}()
	})

	backBtn := widget.NewButton("← Back", func() {
		showChapterView(p, chapterIdx)
	})

	// ── Layout ────────────────────────────────────────────────────────────
	header := container.NewVBox(
		container.NewHBox(backBtn, titleLabel),
		infoLabel,
	)

	sourceCol := container.NewVBox(widget.NewLabel("Source:"), sourceEntry)
	translatedCol := container.NewVBox(
		widget.NewLabel("Translation:"),
		translatedEntry,
		saveBtn,
	)

	retranslateSection := container.NewVBox(
		widget.NewSeparator(),
		widget.NewLabel("Retranslate with overrides:"),
		container.NewGridWithColumns(2,
			widget.NewLabel("Model override:"), modelOverride,
			widget.NewLabel("Thinking mode:"), thinkingSelect,
		),
		container.NewHBox(retranslateBtn, streamingLabel),
	)

	content := container.NewVBox(
		header,
		container.NewGridWithColumns(2, sourceCol, translatedCol),
		retranslateSection,
	)

	scroll := container.NewVScroll(content)

	projectList := buildProjectList()
	split := container.NewHSplit(projectList, scroll)
	split.SetOffset(0.28)
	mainWindow.SetContent(split)
}
