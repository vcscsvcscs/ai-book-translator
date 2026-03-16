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
        request_timeout = config.get("request_timeout", 120.0)
        num_predict = config.get("num_predict")
        
        print(f"🤖 Initializing Ollama with model: {model} at {base_url}")
        
        # Headers (e.g. API key)
        additional_kwargs = {}
        if config.get("api_key"):
            additional_kwargs["headers"] = {"Authorization": f"Bearer {config['api_key']}"}
        
        # Options sent to server (Ollama / llama.cpp) per request
        if num_predict is not None:
            additional_kwargs["num_predict"] = int(num_predict)
        for key in ("repeat_penalty", "top_k", "top_p", "min_p", "presence_penalty"):
            if key in config and config[key] is not None:
                additional_kwargs[key] = config[key]
        if "chat_template_kwargs" in config and config["chat_template_kwargs"]:
            additional_kwargs["chat_template_kwargs"] = config["chat_template_kwargs"]
        
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
            "qwen3.5:9b",
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
            "request_timeout": 120.0,
            "num_predict": None,
            "repeat_penalty": None,
            "top_k": None,
            "top_p": None,
            "min_p": None,
            "presence_penalty": None,
            "chat_template_kwargs": None,
            "api_key": "your-secret-api-key-here",
        }