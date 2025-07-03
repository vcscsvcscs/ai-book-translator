"""
Ollama LLM provider implementation.
"""
from typing import Dict, Any
from llama_index.core.llms import LLM
from llama_index.llms.ollama import Ollama
from ..base import BaseLLMProvider
from utils.exceptions import ConfigurationError

class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider."""
    
    @staticmethod
    def create_llm(config: Dict[str, Any]) -> LLM:
        """Create Ollama LLM instance."""
        OllamaProvider.validate_config(config)
        
        model = config.get("model", "llama3.1")
        base_url = config.get("base_url", "http://localhost:11434")
        temperature = config.get("temperature", 0.2)
        request_timeout = config.get("request_timeout", 60.0)
        
        print(f"🤖 Initializing Ollama with model: {model} at {base_url}")
        
        # Add API key to headers if provided
        additional_kwargs = {}
        if "api_key" in config:
            additional_kwargs["headers"] = {"Authorization": f"Bearer {config['api_key']}"}
        
        return Ollama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            request_timeout=request_timeout,
            additional_kwargs=additional_kwargs,
        )
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate Ollama configuration."""
        required_keys = OllamaProvider.get_required_config_keys()
        for key in required_keys:
            if key not in config or not config[key]:
                raise ConfigurationError(f"Ollama {key} is required")
        
        # Validate base_url format
        base_url = config.get("base_url", "http://localhost:11434")
        if not base_url.startswith(("http://", "https://")):
            raise ConfigurationError(
                "Ollama base_url must start with http:// or https://"
            )
        
        common_models = [
            "llama3.1",
            "llama3",
            "llama2",
            "mistral",
            "codellama",
            "phi",
            "gemma",
            "qwen",
            "qwen2",
            "qwen2-puli-trio",
            "dolphin-mistral",
            "neural-chat",
        ]
        
        model = config.get("model", "llama3.1")
        if model not in common_models:
            print(
                f"⚠️  Warning: Model '{model}' not in common Ollama models. Make sure it's available at {base_url}."
            )
        
        return True
    
    @staticmethod
    def get_required_config_keys() -> list:
        """Return required configuration keys."""
        return ["model", "base_url"]
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "model": "llama3.1",
            "base_url": "http://localhost:11434",
            "temperature": 0.2,
            "request_timeout": 60.0,
            "api_key": "your-secret-api-key-here"
        }