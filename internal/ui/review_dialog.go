package ui

import (
	"fmt"
	"strconv"

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

	backBtn := widget.NewButton("← Back", func() {
		showChapterView(p, chapterIdx)
	})

	// ── Source ────────────────────────────────────────────────────────────
	sourceEntry := widget.NewMultiLineEntry()
	sourceEntry.SetText(chunk.SourceText)
	sourceEntry.Disable()
	sourceEntry.Wrapping = fyne.TextWrapWord

	// ── Translation ───────────────────────────────────────────────────────
	translatedEntry := widget.NewMultiLineEntry()
	translatedEntry.SetText(chunk.TranslatedText)
	translatedEntry.SetPlaceHolder("No translation yet")
	translatedEntry.Wrapping = fyne.TextWrapWord

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

	// ── Thinking log ──────────────────────────────────────────────────────
	thinkLog := widget.NewMultiLineEntry()
	thinkLog.Disable()
	thinkLog.Wrapping = fyne.TextWrapWord
	thinkLog.SetPlaceHolder("Thinking output will stream here during retranslation…")

	thinkLogScroll := container.NewVScroll(thinkLog)

	// Tabs: Translation | Thinking
	tabs := container.NewAppTabs(
		container.NewTabItem("Translation", container.NewBorder(nil, saveBtn, nil, nil,
			container.NewVScroll(translatedEntry),
		)),
		container.NewTabItem("Thinking", thinkLogScroll),
	)
	tabs.SetTabLocation(container.TabLocationTop)

	// Source scroll
	sourceScroll := container.NewVScroll(sourceEntry)

	// Main content split: source left, translation+thinking right
	contentSplit := container.NewHSplit(
		container.NewBorder(widget.NewLabel("Source:"), nil, nil, nil, sourceScroll),
		container.NewBorder(nil, nil, nil, nil, tabs),
	)
	contentSplit.SetOffset(0.45)

	// ── Retranslate controls ──────────────────────────────────────────────
	providerSelect := widget.NewSelect(
		[]string{model.ProviderOllama, model.ProviderDlgoHTTP, model.ProviderDlgo},
		nil,
	)
	providerSelect.SetSelected(p.Provider)

	providerURLEntry := widget.NewEntry()
	providerURLEntry.SetText(p.ProviderURL)
	providerURLEntry.SetPlaceHolder("Provider URL")

	modelEntry := widget.NewEntry()
	modelEntry.SetText(p.ModelPath)

	ollamaModelSelect := widget.NewSelect(nil, func(s string) { modelEntry.SetText(s) })
	ollamaModelSelect.PlaceHolder = "Fetch models…"
	fetchBtn := widget.NewButton("Fetch", func() {
		url := providerURLEntry.Text
		if url == "" {
			url = translator.DefaultOllamaURL
		}
		models, err := translator.ListOllamaModels(url)
		if err != nil {
			dialog.ShowError(err, mainWindow)
			return
		}
		ollamaModelSelect.Options = models
		ollamaModelSelect.Refresh()
		if len(models) > 0 {
			ollamaModelSelect.SetSelected(models[0])
		}
	})

	temperatureEntry := widget.NewEntry()
	temperatureEntry.SetText(fmt.Sprintf("%.2f", p.ModelParams.Temperature))

	maxTokensEntry := widget.NewEntry()
	maxTokensEntry.SetText(strconv.Itoa(p.ModelParams.MaxTokens))

	thinkingSelect := widget.NewSelect(
		[]string{model.ThinkingDisabled, model.ThinkingEnabled, model.ThinkingBudget},
		nil,
	)
	thinkingSelect.SetSelected(p.ModelParams.ThinkingMode)

	thinkingBudgetEntry := widget.NewEntry()
	thinkingBudgetEntry.SetPlaceHolder("Budget (budget mode only)")
	thinkingBudgetEntry.SetText(strconv.Itoa(p.ModelParams.ThinkingBudget))

	minPEntry := widget.NewEntry()
	minPEntry.SetText(fmt.Sprintf("%.2f", p.ModelParams.MinP))

	presencePenaltyEntry := widget.NewEntry()
	presencePenaltyEntry.SetText(fmt.Sprintf("%.2f", p.ModelParams.PresencePenalty))

	repetitionPenaltyEntry := widget.NewEntry()
	repetitionPenaltyEntry.SetText(fmt.Sprintf("%.2f", p.ModelParams.RepetitionPenalty))

	// Qwen3 preset loader
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
		thinkingSelect.SetSelected(preset.ThinkingMode)
		minPEntry.SetText(fmt.Sprintf("%.2f", preset.MinP))
		presencePenaltyEntry.SetText(fmt.Sprintf("%.2f", preset.PresencePenalty))
		repetitionPenaltyEntry.SetText(fmt.Sprintf("%.2f", preset.RepetitionPenalty))
	})
	presetSelect.PlaceHolder = "Load preset…"

	statusLabel := widget.NewLabel("")

	retranslateBtn := widget.NewButton("Retranslate", func() {
		params := p.ModelParams
		params.ThinkingMode = thinkingSelect.Selected
		if t, err := strconv.ParseFloat(temperatureEntry.Text, 32); err == nil {
			params.Temperature = float32(t)
		}
		if n, err := strconv.Atoi(maxTokensEntry.Text); err == nil {
			params.MaxTokens = n
		}
		if b, err := strconv.Atoi(thinkingBudgetEntry.Text); err == nil {
			params.ThinkingBudget = b
		}

		modelPath := modelEntry.Text
		if ollamaModelSelect.Selected != "" && providerSelect.Selected == model.ProviderOllama {
			modelPath = ollamaModelSelect.Selected
		}

		tr := translator.New(appStore)
		statusLabel.SetText("Translating…")
		translatedEntry.SetText("")
		thinkLog.SetText("")

		go func() {
			err := tr.RetranslateChunk(
				p, chapterIdx, chunkIdx,
				providerSelect.Selected,
				providerURLEntry.Text,
				modelPath,
				params,
				func(e translator.ProgressEvent) {
					fyne.Do(func() {
						if e.EventType == translator.EventToken {
							if e.IsThinking {
								// Switch to thinking tab and stream there
								tabs.SelectIndex(1)
								thinkLog.SetText(thinkLog.Text + e.Token)
								thinkLogScroll.ScrollToBottom()
							} else {
								// Switch back to translation tab when real tokens start
								tabs.SelectIndex(0)
								translatedEntry.SetText(translatedEntry.Text + e.Token)
							}
						}
						if e.EventType == translator.EventChunkDone || e.EventType == translator.EventChunkFailed {
							statusLabel.SetText("")
						}
					})
				},
			)
			fyne.Do(func() {
				if err != nil {
					dialog.ShowError(err, mainWindow)
					statusLabel.SetText("")
					return
				}
				reloaded, loadErr := appStore.Load(p.ID)
				if loadErr == nil {
					showReviewDialog(reloaded, chapterIdx, chunkIdx)
				}
			})
		}()
	})

	// Collapsible retranslate options
	optionsForm := &widget.Form{Items: []*widget.FormItem{
		{Text: "Provider", Widget: providerSelect},
		{Text: "Provider URL", Widget: providerURLEntry},
		{Text: "Model", Widget: modelEntry},
		{Text: "Ollama Models", Widget: container.NewBorder(nil, nil, nil, fetchBtn, ollamaModelSelect)},
		{Text: "Temperature", Widget: temperatureEntry},
		{Text: "Max Tokens", Widget: maxTokensEntry},
		{Text: "Thinking Mode", Widget: thinkingSelect},
		{Text: "Think Budget", Widget: thinkingBudgetEntry},
	}}

	optionsAccordion := widget.NewAccordion(
		widget.NewAccordionItem("Retranslate Options", optionsForm),
	)

	footer := container.NewVBox(
		widget.NewSeparator(),
		optionsAccordion,
		container.NewHBox(retranslateBtn, statusLabel),
	)

	header := container.NewVBox(
		container.NewHBox(backBtn, titleLabel),
		infoLabel,
	)

	view := container.NewBorder(header, footer, nil, nil, contentSplit)

	projectList := buildProjectList()
	split := container.NewHSplit(projectList, view)
	split.SetOffset(0.28)
	mainWindow.SetContent(split)
}
