"""
Google Gemini LLM provider implementation.
"""

from typing import Dict, Any
from llama_index.core.llms import LLM
from llama_index.llms.gemini import Gemini

from ..base import BaseLLMProvider
from utils.exceptions import ConfigurationError


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider."""

    @staticmethod
    def create_llm(config: Dict[str, Any]) -> LLM:
        """Create Gemini LLM instance."""
        GeminiProvider.validate_config(config)

        api_key = config["api_key"]
        model = config.get("model", "gemini-2.5-flash-preview-05-20")
        temperature = config.get("temperature", 0.2)
        max_tokens = config.get("max_tokens", None)
        top_p = config.get("top_p", 0.95)
        top_k = config.get("top_k", 64)

        print(f"🤖 Initializing Gemini with model: {model}")

        return Gemini(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
        )

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate Gemini configuration."""
        required_keys = GeminiProvider.get_required_config_keys()

        for key in required_keys:
            if key not in config or not config[key]:
                raise ConfigurationError(f"Gemini {key} is required")

        # Check for placeholder values
        if config["api_key"] in ["YOUR_GEMINI_API_KEY", ""]:
            raise ConfigurationError("Please set your actual Gemini API key")

        # Validate model if specified
        valid_models = [
            "gemini-2.5-flash-preview-05-20",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
            "gemini-pro",
            "gemini-pro-vision",
        ]
        model = config.get("model", "gemini-2.5-flash-preview-05-20")
        if model not in valid_models:
            print(
                f"⚠️  Warning: Model '{model}' not in known Gemini models: {valid_models}"
            )

        # Validate temperature range
        temperature = config.get("temperature", 0.2)
        if not (0.0 <= temperature <= 1.0):
            raise ConfigurationError("Gemini temperature must be between 0.0 and 1.0")

        # Validate top_p range
        top_p = config.get("top_p", 0.95)
        if not (0.0 <= top_p <= 1.0):
            raise ConfigurationError("Gemini top_p must be between 0.0 and 1.0")

        # Validate top_k
        top_k = config.get("top_k", 64)
        if not isinstance(top_k, int) or top_k < 1:
            raise ConfigurationError("Gemini top_k must be a positive integer")

        return True

    @staticmethod
    def get_required_config_keys() -> list:
        """Return required configuration keys."""
        return ["api_key"]

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "model": "gemini-2.5-flash-preview-05-20",
            "temperature": 0.2,
            "max_tokens": None,
            "top_p": 0.95,
            "top_k": 64,
        }
