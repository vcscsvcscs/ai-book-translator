//go:build !linux

package translator

import "fmt"

func NewDlgoBackend(modelPath string) (LLMBackend, error) {
	return nil, fmt.Errorf(
		"direct dlgo loading is only supported on Linux; use HTTP backend instead: "+
			"run 'dlgo server --model %s' and configure the app to use HTTP mode", modelPath)
}
