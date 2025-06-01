"""
Configuration loading and validation.
"""

import yaml
from pathlib import Path
from typing import Dict, Any

from utils.exceptions import ConfigurationError


class ConfigLoader:
    """Handles configuration loading and validation."""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._config = None
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading config file: {e}")
        
        self._validate_config()
        return self._config
    
    def _validate_config(self):
        """Validate configuration structure."""
        if not isinstance(self._config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        # Check for at least one provider configuration
        providers = ["openai", "azure", "gemini", "ollama"]
        if not any(provider in self._config for provider in providers):
            raise ConfigurationError(f"At least one provider must be configured: {providers}")
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        if not self._config:
            raise ConfigurationError("Configuration not loaded")
        
        if provider not in self._config:
            raise ConfigurationError(f"Provider '{provider}' not configured")
        
        return self._config[provider]
    
    def validate_provider(self, provider: str):
        """Validate that a provider is properly configured."""
        config = self.get_provider_config(provider)
        
        if provider == "openai":
            self._validate_openai_config(config)
        elif provider == "azure":
            self._validate_azure_config(config)
        elif provider == "gemini":
            self._validate_gemini_config(config)
        elif provider == "ollama":
            self._validate_ollama_config(config)
        else:
            raise ConfigurationError(f"Unknown provider: {provider}")
    
    def _validate_openai_config(self, config: Dict[str, Any]):
        """Validate OpenAI configuration."""
        if not config.get("api_key"):
            raise ConfigurationError("OpenAI API key is required")
        
        if config.get("api_key") == "YOUR_OPENAI_API_KEY":
            raise ConfigurationError("Please set your actual OpenAI API key")
    
    def _validate_azure_config(self, config: Dict[str, Any]):
        """Validate Azure OpenAI configuration."""
        required_fields = ["api_key", "endpoint", "deployment_name"]
        for field in required_fields:
            if not config.get(field):
                raise ConfigurationError(f"Azure {field} is required")
        
        endpoint = config.get("endpoint")
        if not endpoint or not endpoint.startswith("https://"):
            raise ConfigurationError("Azure endpoint must be a valid HTTPS URL")
    
    def _validate_gemini_config(self, config: Dict[str, Any]):
        """Validate Gemini configuration."""
        if not config.get("api_key"):
            raise ConfigurationError("Gemini API key is required")
        
        if config.get("api_key") == "YOUR_GEMINI_API_KEY":
            raise ConfigurationError("Please set your actual Gemini API key")
    
    def _validate_ollama_config(self, config: Dict[str, Any]):
        """Validate Ollama configuration."""
        if not config.get("model"):
            raise ConfigurationError("Ollama model name is required")
        
        base_url = config.get("base_url", "http://localhost:11434")
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            raise ConfigurationError("Ollama base_url must be a valid HTTP/HTTPS URL")