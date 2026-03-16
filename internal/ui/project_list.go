package ui

import (
	"fmt"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/widget"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

func buildProjectList() fyne.CanvasObject {
	list := widget.NewList(
		func() int {
			projects, _ := appStore.List()
			return len(projects)
		},
		func() fyne.CanvasObject {
			return container.NewVBox(
				widget.NewLabel("Project Name"),
				widget.NewLabel("Status"),
			)
		},
		func(id widget.ListItemID, obj fyne.CanvasObject) {
			projects, _ := appStore.List()
			if id >= len(projects) {
				return
			}
			p := projects[id]
			box := obj.(*fyne.Container)
			box.Objects[0].(*widget.Label).SetText(p.Name)
			completed, total := p.Progress()
			pct := 0.0
			if total > 0 {
				pct = float64(completed) / float64(total) * 100
			}
			box.Objects[1].(*widget.Label).SetText(
				fmt.Sprintf("%s - %.0f%%", p.Status, pct),
			)
		},
	)

	list.OnSelected = func(id widget.ListItemID) {
		projects, _ := appStore.List()
		if id >= len(projects) {
			return
		}
		showProjectDetail(projects[id])
	}

	newBtn := widget.NewButton("New Project", func() {
		showCreateProject(func() {
			list.Refresh()
		})
	})

	return container.NewBorder(newBtn, nil, nil, nil, list)
}

func refreshProjectList() {
	content := buildMainLayout()
	mainWindow.SetContent(content)
}

func showProjectDetail(p *model.Project) {
	detail := buildProjectDetail(p)

	projectList := buildProjectList()
	split := container.NewHSplit(projectList, detail)
	split.SetOffset(0.3)
	mainWindow.SetContent(split)
}
