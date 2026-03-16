package main

import (
	"os"

	"github.com/vcscsvcscs/ai-book-translator/internal/cli"
)

func main() {
	if err := cli.Execute(); err != nil {
		os.Exit(1)
	}
}
