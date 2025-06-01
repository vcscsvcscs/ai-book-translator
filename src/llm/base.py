"""
Base provider interface for LLM implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from llama_index.core.llms import LLM


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @staticmethod
    @abstractmethod
    def create_llm(config: Dict[str, Any]) -> LLM:
        """Create and return an LLM instance based on configuration."""
        pass
    
    @staticmethod
    @abstractmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate provider-specific configuration."""
        pass
    
    @staticmethod
    @abstractmethod
    def get_required_config_keys() -> list:
        """Return list of required configuration keys."""
        pass
    
    @staticmethod
    @abstractmethod
    def get_default_config() -> Dict[str, Any]:
        """Return default configuration values."""
        pass