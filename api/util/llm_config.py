import os
import json
from typing import Optional
from lib.fact_extractor.llm_provider_config import create_llm_config
from lib.fact_extractor.models import LLMConfig

# Global default LLM config from environment variables
llm_config = create_llm_config()


def is_ollama_enabled() -> bool:
    """Check if Ollama provider is specifically enabled via environment variable."""
    return os.environ.get("OLLAMA_ENABLED", "false").lower() in ("true", "1", "yes")


def get_api_key_for_provider(provider: str) -> str:
    """Get API key from environment for the given provider."""
    keys = {
        "openai": os.environ.get("OPENAI_API_KEY", ""),
        "deepinfra": os.environ.get("DEEPINFRA_API_TOKEN", ""),
        "ollama": os.environ.get("OLLAMA_API_KEY", "openai_api_key")
    }
    return keys.get(provider, "")


def get_default_base_url(provider: str) -> str:
    """Get default base URL for the given provider."""
    defaults = {
        "openai": "https://api.openai.com/v1",
        "ollama": "http://localhost:11434/v1",
        "deepinfra": "https://api.deepinfra.com/v1/openai"
    }
    return defaults.get(provider, "https://api.openai.com/v1")


def build_llm_config_from_db_model(db_model, api_key: str) -> LLMConfig:
    """
    Build LLMConfig from database LLMModel.

    Args:
        db_model: The LLMModel database object
        api_key: API key for the provider

    Returns:
        LLMConfig object ready to use with FactExtractor
    """
    model_kwargs = {}
    if db_model.model_kwargs_json:
        try:
            model_kwargs = json.loads(db_model.model_kwargs_json)
        except json.JSONDecodeError:
            pass

    # Use custom base_url if provided, otherwise use default
    base_url = db_model.base_url if db_model.base_url else get_default_base_url(db_model.provider)

    return LLMConfig(
        provider=db_model.provider,
        base_url=base_url,
        api_key=api_key,
        model_name=db_model.model_identifier,
        temperature=db_model.temperature,
        max_tokens=db_model.max_tokens,
        timeout=db_model.timeout,
        model_kwargs=model_kwargs
    )