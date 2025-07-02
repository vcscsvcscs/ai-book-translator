"""
Azure OpenAI LLM provider implementation.
"""
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import httpx

from typing import Dict, Any
from llama_index.core.llms import LLM
from llama_index.llms.azure_openai import AzureOpenAI

from ..base import BaseLLMProvider
from utils.exceptions import ConfigurationError


class AzureProvider(BaseLLMProvider):
    """Azure OpenAI LLM provider."""

    @staticmethod
    def create_llm(config: Dict[str, Any]) -> LLM:
        """Create Azure OpenAI LLM instance."""
        AzureProvider.validate_config(config)

        api_key = config.get("api_key")
        endpoint = config["endpoint"]
        api_version = config.get("api_version", "2024-02-01")
        deployment_name = config["deployment_name"]
        temperature = config.get("temperature", 0.2)
        max_tokens = config.get("max_tokens", None)

        print(f"🤖 Initializing Azure OpenAI with deployment: {deployment_name}")

        if not api_key:
            credential = DefaultAzureCredential(
                exclude_workload_identity_credential=True,
                exclude_managed_identity_credential=True,
                exclude_developer_cli_credential=True,
            )

            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )

            return AzureOpenAI(
                api_version=api_version,
                use_azure_ad=True,
                azure_endpoint=endpoint,
                engine=deployment_name,
                http_client=httpx.Client(http2=True),
                azure_deployment=deployment_name,
                azure_ad_token_provider=token_provider,
            )

        return AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            azure_deployment=deployment_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate Azure OpenAI configuration."""
        required_keys = AzureProvider.get_required_config_keys()

        for key in required_keys:
            if key not in config or not config[key]:
                raise ConfigurationError(f"Azure OpenAI {key} is required")

        # Check for placeholder values
        placeholder_values = {
            "endpoint": ["https://your-resource-name.openai.azure.com/", ""],
            "deployment_name": ["your-deployment-name", ""],
        }

        for key, placeholders in placeholder_values.items():
            if config[key] in placeholders:
                raise ConfigurationError(f"Please set your actual Azure OpenAI {key}")

        # Validate endpoint format
        endpoint = config["endpoint"]
        if not endpoint.startswith("https://") or not endpoint.endswith("/"):
            raise ConfigurationError(
                "Azure endpoint should start with 'https://' and end with '/'"
            )

        if "openai.azure.com" not in endpoint:
            print(
                f"⚠️  Warning: Endpoint '{endpoint}' doesn't appear to be a standard Azure OpenAI endpoint"
            )

        # Validate API version format
        api_version = config.get("api_version", "2024-02-01")
        valid_versions = [
            "2024-02-01",
            "2023-12-01-preview",
            "2023-10-01-preview",
            "2023-08-01-preview",
            "2023-06-01-preview",
            "2023-05-15",
            "2025-01-01-preview",
        ]
        if api_version not in valid_versions:
            print(
                f"⚠️  Warning: API version '{api_version}' not in known versions: {valid_versions}"
            )

        return True

    @staticmethod
    def get_required_config_keys() -> list:
        """Return required configuration keys."""
        return ["endpoint", "deployment_name"]

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "api_version": "2024-02-01",
            "temperature": 0.2,
            "max_tokens": None,
        }
