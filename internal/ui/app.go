package ui

import (
	"github.com/vcscsvcscs/ai-book-translator/internal/config"
	"github.com/vcscsvcscs/ai-book-translator/internal/store"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/widget"
)

var (
	appConfig  *config.Config
	appStore   *store.Store
	mainWindow fyne.Window
)

func Run(cfg *config.Config, s *store.Store) {
	appConfig = cfg
	appStore = s

	a := app.NewWithID("com.vcscsvcscs.ai-book-translator")
	mainWindow = a.NewWindow("AI Book Translator")
	mainWindow.Resize(fyne.NewSize(1100, 720))

	content := buildMainLayout()
	mainWindow.SetContent(content)
	mainWindow.ShowAndRun()
}

func buildMainLayout() fyne.CanvasObject {
	projectList := buildProjectList()
	detail := widget.NewLabel("Select a project from the list, or create a new one.")

	split := container.NewHSplit(projectList, detail)
	split.SetOffset(0.28)

	return split
}
