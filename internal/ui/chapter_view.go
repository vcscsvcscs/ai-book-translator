package ui

import (
	"fmt"
	"strings"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/widget"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

func showChapterView(p *model.Project, chapterIdx int) {
	ch := &p.Chapters[chapterIdx]

	title := widget.NewLabel(fmt.Sprintf("Chapter %d: %s", ch.Index, ch.Title))
	title.TextStyle = fyne.TextStyle{Bold: true}

	cc, ct := ch.Progress()
	progress := widget.NewLabel(fmt.Sprintf("%d/%d chunks completed", cc, ct))

	backBtn := widget.NewButton("Back", func() {
		showProjectDetail(p)
	})

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

			icon := statusTag(c.Status)
			box.Objects[0].(*widget.Label).SetText(icon)

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
		progress,
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
