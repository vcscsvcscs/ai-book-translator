//go:build linux

package translator

import (
	"context"
	"fmt"

	"github.com/computerex/dlgo"
)

type dlgoBackend struct {
	model *dlgo.LLM
}

func NewDlgoBackend(modelPath string) (LLMBackend, error) {
	m, err := dlgo.LoadLLM(modelPath)
	if err != nil {
		return nil, fmt.Errorf("load dlgo model: %w", err)
	}
	return &dlgoBackend{model: m}, nil
}

func (d *dlgoBackend) ChatStream(_ context.Context, system, user string, onToken func(string), opts LLMOptions) error {
	dlgoOpts := []dlgo.Option{
		dlgo.WithMaxTokens(opts.MaxTokens),
		dlgo.WithTemperature(opts.Temperature),
		dlgo.WithTopK(opts.TopK),
		dlgo.WithTopP(opts.TopP),
	}
	return d.model.ChatStream(system, user, onToken, dlgoOpts...)
}

func (d *dlgoBackend) Close() {}
