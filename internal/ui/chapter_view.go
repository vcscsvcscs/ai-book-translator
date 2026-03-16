package ui

import (
	"fmt"
	"strings"
	"sync"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/widget"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
	"github.com/vcscsvcscs/ai-book-translator/internal/translator"
)

func showChapterView(p *model.Project, chapterIdx int) {
	ch := &p.Chapters[chapterIdx]

	title := widget.NewLabel(fmt.Sprintf("Chapter %d: %s", ch.Index, ch.Title))
	title.TextStyle = fyne.TextStyle{Bold: true}

	cc, ct := ch.Progress()
	progressLabel := widget.NewLabel(fmt.Sprintf("%d/%d chunks completed", cc, ct))
	progressBar := widget.NewProgressBar()
	if ct > 0 {
		progressBar.SetValue(float64(cc) / float64(ct))
	}

	backBtn := widget.NewButton("← Back", func() {
		showProjectDetail(p)
	})

	logEntry := widget.NewMultiLineEntry()
	logEntry.SetMinRowsVisible(4)
	logEntry.Disable()
	logEntry.SetPlaceHolder("Translation log…")
	logScroll := container.NewVScroll(logEntry)
	logScroll.SetMinSize(fyne.NewSize(0, 90))

	var mu sync.Mutex
	var translating bool

	translateBtn := widget.NewButton("Translate Chapter", nil)
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
		logEntry.SetText("")

		t := translator.New(appStore)
		go func() {
			t.TranslateChapter(p, chapterIdx, func(e translator.ProgressEvent) {
				fyne.Do(func() {
					switch e.EventType {
					case translator.EventChunkStart:
						appendLog(logEntry, fmt.Sprintf("[chunk %d] translating…", e.ChunkIndex))
					case translator.EventChunkDone:
						c, tot := ch.Progress()
						progressLabel.SetText(fmt.Sprintf("%d/%d chunks completed", c, tot))
						if tot > 0 {
							progressBar.SetValue(float64(c) / float64(tot))
						}
						appendLog(logEntry, fmt.Sprintf("  chunk %d done", e.ChunkIndex))
					case translator.EventChunkFailed:
						appendLog(logEntry, fmt.Sprintf("  chunk %d FAILED: %v", e.ChunkIndex, e.Error))
					}
				})
			})

			fyne.Do(func() {
				mu.Lock()
				translating = false
				mu.Unlock()
				translateBtn.SetText("Translate Chapter")
				translateBtn.Enable()

				reloaded, err := appStore.Load(p.ID)
				if err == nil {
					showChapterView(reloaded, chapterIdx)
				}
			})
		}()
	}

	list := widget.NewList(
		func() int { return len(ch.Chunks) },
		func() fyne.CanvasObject {
			return container.NewHBox(
				widget.NewLabel("[  ]"),
				widget.NewLabel("Chunk preview"),
			)
		},
		func(id widget.ListItemID, obj fyne.CanvasObject) {
			if id >= len(ch.Chunks) {
				return
			}
			c := &ch.Chunks[id]
			box := obj.(*fyne.Container)
			box.Objects[0].(*widget.Label).SetText(statusTag(c.Status))
			preview := c.TranslatedText
			if preview == "" {
				preview = c.SourceText
			}
			preview = strings.ReplaceAll(preview, "\n", " ")
			if len(preview) > 80 {
				preview = preview[:77] + "..."
			}
			box.Objects[1].(*widget.Label).SetText(fmt.Sprintf("[%d] %s", c.Index, preview))
		},
	)

	list.OnSelected = func(id widget.ListItemID) {
		if id >= len(ch.Chunks) {
			return
		}
		showReviewDialog(p, chapterIdx, id)
	}

	header := container.NewVBox(
		container.NewHBox(backBtn, title),
		progressBar,
		container.NewHBox(progressLabel, translateBtn),
		logScroll,
	)

	view := container.NewBorder(header, nil, nil, nil, list)

	projectList := buildProjectList()
	split := container.NewHSplit(projectList, view)
	split.SetOffset(0.3)
	mainWindow.SetContent(split)
}

func statusTag(status string) string {
	switch status {
	case model.ChunkCompleted:
		return "[OK]"
	case model.ChunkFailed:
		return "[FAIL]"
	case model.ChunkRevised:
		return "[REV]"
	case model.ChunkTranslating:
		return "[...]"
	default:
		return "[  ]"
	}
}
