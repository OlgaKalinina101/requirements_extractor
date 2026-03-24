"""Factory for creating LLM clients based on application configuration."""

from src.config import ApplicationConfig
from src.llm.base_client import BaseLLMClient


def create_llm_client(config: ApplicationConfig) -> BaseLLMClient:
    """Create an LLM client for the configured provider.

    Args:
        config: Application configuration with provider and API settings.

    Returns:
        Configured LLM client instance (OpenRouter or DeepSeek).

    Raises:
        ValueError: If provider is not supported.
    """
    provider = config.provider.lower()
    if provider == "openrouter":
        from src.openrouter_client import OpenRouterClient
        return OpenRouterClient(config.openrouter)
    if provider == "deepseek":
        from src.deepseek_client import DeepSeekClient
        return DeepSeekClient(config.deepseek)
    raise ValueError(
        f"Unknown provider: {provider}. "
        "Supported: 'openrouter' (recommended) or 'deepseek' (legacy)"
    )
