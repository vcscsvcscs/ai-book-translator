package ui

import (
	"context"
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
	translatedScroll := container.NewVScroll(translatedEntry)
	sourceScroll := container.NewVScroll(sourceEntry)

	// local accumulators so we don't read .Text on disabled widgets
	var thinkBuf, transBuf string

	// Three-panel split: source | translation | thinking
	sourcePanel := container.NewBorder(widget.NewLabel("Source"), nil, nil, nil, sourceScroll)
	translationPanel := container.NewBorder(widget.NewLabel("Translation"), saveBtn, nil, nil, translatedScroll)
	thinkingPanel := container.NewBorder(widget.NewLabel("Thinking"), nil, nil, nil, thinkLogScroll)

	contentSplit := container.NewHSplit(
		sourcePanel,
		container.NewHSplit(translationPanel, thinkingPanel),
	)
	contentSplit.SetOffset(0.33)

	// ── Cancellation ─────────────────────────────────────────────────────
	var cancelFn context.CancelFunc

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

	topKEntry := widget.NewEntry()
	topKEntry.SetText(strconv.Itoa(p.ModelParams.TopK))

	minPEntry := widget.NewEntry()
	minPEntry.SetText(fmt.Sprintf("%.2f", p.ModelParams.MinP))

	presencePenaltyEntry := widget.NewEntry()
	presencePenaltyEntry.SetText(fmt.Sprintf("%.2f", p.ModelParams.PresencePenalty))

	repetitionPenaltyEntry := widget.NewEntry()
	repetitionPenaltyEntry.SetText(fmt.Sprintf("%.2f", p.ModelParams.RepetitionPenalty))

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
		thinkingSelect.SetSelected(preset.ThinkingMode)
		minPEntry.SetText(fmt.Sprintf("%.2f", preset.MinP))
		presencePenaltyEntry.SetText(fmt.Sprintf("%.2f", preset.PresencePenalty))
		repetitionPenaltyEntry.SetText(fmt.Sprintf("%.2f", preset.RepetitionPenalty))
	})
	presetSelect.PlaceHolder = "Load preset…"

	statusLabel := widget.NewLabel("")

	stopBtn := widget.NewButton("Stop", func() {
		if cancelFn != nil {
			cancelFn()
		}
	})
	stopBtn.Disable()

	retranslateBtn := widget.NewButton("Retranslate", func() {
		params := p.ModelParams
		params.ThinkingMode = thinkingSelect.Selected
		if t, err := strconv.ParseFloat(temperatureEntry.Text, 32); err == nil {
			params.Temperature = float32(t)
		}
		if n, err := strconv.Atoi(maxTokensEntry.Text); err == nil {
			params.MaxTokens = n
		}
		if n, err := strconv.Atoi(topKEntry.Text); err == nil {
			params.TopK = n
		}
		if b, err := strconv.Atoi(thinkingBudgetEntry.Text); err == nil {
			params.ThinkingBudget = b
		}
		if v, err := strconv.ParseFloat(minPEntry.Text, 32); err == nil {
			params.MinP = float32(v)
		}
		if v, err := strconv.ParseFloat(presencePenaltyEntry.Text, 32); err == nil {
			params.PresencePenalty = float32(v)
		}
		if v, err := strconv.ParseFloat(repetitionPenaltyEntry.Text, 32); err == nil {
			params.RepetitionPenalty = float32(v)
		}

		modelPath := modelEntry.Text
		if ollamaModelSelect.Selected != "" && providerSelect.Selected == model.ProviderOllama {
			modelPath = ollamaModelSelect.Selected
		}

		ctx, cancel := context.WithCancel(context.Background())
		cancelFn = cancel

		tr := translator.New(appStore)
		statusLabel.SetText("Translating…")
		thinkBuf = ""
		transBuf = ""
		translatedEntry.SetText("")
		thinkLog.SetText("")
		stopBtn.Enable()

		go func() {
			err := tr.RetranslateChunk(
				ctx,
				p, chapterIdx, chunkIdx,
				providerSelect.Selected,
				providerURLEntry.Text,
				modelPath,
				params,
				func(e translator.ProgressEvent) {
					fyne.Do(func() {
						if e.EventType == translator.EventToken {
							if e.IsThinking {
								thinkBuf += e.Token
								thinkLog.SetText(thinkBuf)
								thinkLogScroll.ScrollToBottom()
							} else {
								transBuf += e.Token
								translatedEntry.SetText(transBuf)
								translatedScroll.ScrollToBottom()
							}
						}
						if e.EventType == translator.EventChunkDone || e.EventType == translator.EventChunkFailed {
							statusLabel.SetText("")
							stopBtn.Disable()
						}
					})
				},
			)
			fyne.Do(func() {
				stopBtn.Disable()
				cancel()
				if err != nil && ctx.Err() == nil {
					dialog.ShowError(err, mainWindow)
					statusLabel.SetText("")
					return
				}
				if ctx.Err() != nil {
					statusLabel.SetText("Stopped.")
					return
				}
				reloaded, loadErr := appStore.Load(p.ID)
				if loadErr == nil {
					showReviewDialog(reloaded, chapterIdx, chunkIdx)
				}
			})
		}()
	})

	optionsForm := &widget.Form{Items: []*widget.FormItem{
		{Text: "Preset", Widget: presetSelect},
		{Text: "Provider", Widget: providerSelect},
		{Text: "Provider URL", Widget: providerURLEntry},
		{Text: "Model", Widget: modelEntry},
		{Text: "Ollama Models", Widget: container.NewBorder(nil, nil, nil, fetchBtn, ollamaModelSelect)},
		{Text: "Temperature", Widget: temperatureEntry},
		{Text: "Max Tokens", Widget: maxTokensEntry},
		{Text: "Top K", Widget: topKEntry},
		{Text: "Min P", Widget: minPEntry},
		{Text: "Presence Penalty", Widget: presencePenaltyEntry},
		{Text: "Repetition Penalty", Widget: repetitionPenaltyEntry},
		{Text: "Thinking Mode", Widget: thinkingSelect},
		{Text: "Think Budget", Widget: thinkingBudgetEntry},
	}}

	optionsAccordion := widget.NewAccordion(
		widget.NewAccordionItem("Retranslate Options", optionsForm),
	)

	footer := container.NewVBox(
		widget.NewSeparator(),
		optionsAccordion,
		container.NewHBox(retranslateBtn, stopBtn, statusLabel),
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
