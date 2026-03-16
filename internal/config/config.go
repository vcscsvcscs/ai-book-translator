package config

import (
	"os"
	"path/filepath"

	"github.com/spf13/viper"
	"github.com/vcscsvcscs/ai-book-translator/internal/model"
)

const (
	AppName    = "abt"
	ConfigName = "config"
	ConfigType = "yaml"
)

type Config struct {
	ModelsDir   string `mapstructure:"models_dir"`
	DataDir     string `mapstructure:"data_dir"`
	Provider    string `mapstructure:"provider"`
	OllamaURL   string `mapstructure:"ollama_url"`
	DlgoURL     string `mapstructure:"dlgo_url"`
}

func defaultDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = "."
	}
	return filepath.Join(home, ".abt")
}

func Load() (*Config, error) {
	base := defaultDir()

	viper.SetDefault("models_dir", filepath.Join(base, "models"))
	viper.SetDefault("data_dir", filepath.Join(base, "projects"))
	viper.SetDefault("provider", model.ProviderOllama)
	viper.SetDefault("ollama_url", "http://localhost:11434")
	viper.SetDefault("dlgo_url", "http://localhost:8080")

	viper.SetConfigName(ConfigName)
	viper.SetConfigType(ConfigType)
	viper.AddConfigPath(base)
	viper.AddConfigPath(".")

	viper.SetEnvPrefix("ABT")
	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, err
		}
	}

	cfg := &Config{}
	if err := viper.Unmarshal(cfg); err != nil {
		return nil, err
	}

	if err := os.MkdirAll(cfg.ModelsDir, 0o755); err != nil {
		return nil, err
	}
	if err := os.MkdirAll(cfg.DataDir, 0o755); err != nil {
		return nil, err
	}

	return cfg, nil
}
