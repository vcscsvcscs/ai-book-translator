"""
Factory for creating LLM instances.
"""

from typing import Dict, Any
from llama_index.core.llms import LLM

from .providers.openai_provider import OpenAIProvider
from .providers.azure_provider import AzureProvider
from .providers.gemini_provider import GeminiProvider
from .providers.ollama_provider import OllamaProvider
from utils.exceptions import ConfigurationError


class LLMFactory:
    """Factory class for creating LLM instances."""
    
    PROVIDERS = {
        "openai": OpenAIProvider,
        "azure": AzureProvider,
        "gemini": GeminiProvider,
        "ollama": OllamaProvider,
    }
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def create_llm(self, provider: str) -> LLM:
        """Create an LLM instance for the specified provider."""
        if provider not in self.PROVIDERS:
            available = ", ".join(self.PROVIDERS.keys())
            raise ConfigurationError(f"Unknown provider '{provider}'. Available: {available}")
        
        if provider not in self.config:
            raise ConfigurationError(f"Provider '{provider}' not configured")
        
        provider_config = self.config[provider]
        provider_class = self.PROVIDERS[provider]
        
        try:
            return provider_class.create_llm(provider_config)
        except Exception as e:
            raise ConfigurationError(f"Failed to create {provider} LLM: {e}")
    
    def list_available_providers(self) -> list:
        """List all available providers."""
        return list(self.PROVIDERS.keys())
    
    def list_configured_providers(self) -> list:
        """List providers that are configured."""
        return [p for p in self.PROVIDERS.keys() if p in self.config]