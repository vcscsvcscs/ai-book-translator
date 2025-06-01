"""
OpenAI LLM provider implementation.
"""

from typing import Dict, Any
from llama_index.core.llms import LLM
from llama_index.llms.openai import OpenAI

from ..base import BaseLLMProvider
from utils.exceptions import ConfigurationError


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider."""

    @staticmethod
    def create_llm(config: Dict[str, Any]) -> LLM:
        """Create OpenAI LLM instance."""
        OpenAIProvider.validate_config(config)

        api_key = config["api_key"]
        model = config.get("model", "gpt-4o")
        temperature = config.get("temperature", 0.2)
        max_tokens = config.get("max_tokens", None)

        print(f"🤖 Initializing OpenAI with model: {model}")

        return OpenAI(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate OpenAI configuration."""
        required_keys = OpenAIProvider.get_required_config_keys()

        for key in required_keys:
            if key not in config or not config[key]:
                raise ConfigurationError(f"OpenAI {key} is required")

        # Check for placeholder values
        if config["api_key"] in ["YOUR_OPENAI_API_KEY", ""]:
            raise ConfigurationError("Please set your actual OpenAI API key")

        # Validate model if specified
        valid_models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]
        model = config.get("model", "gpt-4o")
        if model not in valid_models:
            print(f"⚠️  Warning: Model '{model}' not in known models: {valid_models}")

        return True

    @staticmethod
    def get_required_config_keys() -> list:
        """Return required configuration keys."""
        return ["api_key"]

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "model": "gpt-4o",
            "temperature": 0.2,
            "max_tokens": None,
        }
