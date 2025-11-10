"""
Embedding provider configuration with automatic fallback.
Supports DeepInfra, OpenAI, and Ollama embedding models.
"""
import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding providers."""
    provider: str  # deepinfra, openai, or ollama
    base_url: str
    api_key: str
    model_name: str
    dimensions: int  # Expected embedding dimensions
    timeout: int = 360


def create_embedding_config() -> EmbeddingConfig:
    """
    Create embedding configuration with fallback priority:
    1. DeepInfra (if DEEPINFRA_EMBEDDING_TOKEN or DEEPINFRA_API_TOKEN is set)
    2. OpenAI (if OPENAI_API_KEY is set)
    3. Ollama (local service fallback)
    """

    # Check for DeepInfra configuration first
    deepinfra_token = os.environ.get("DEEPINFRA_EMBEDDING_TOKEN") or os.environ.get("DEEPINFRA_API_TOKEN")
    if deepinfra_token:
        logger.info("Using DeepInfra provider for embeddings")
        return _create_deepinfra_embedding_config(deepinfra_token)

    # Check for OpenAI configuration
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key and openai_key != "openai_api_key":  # Exclude default placeholder
        logger.info("Using OpenAI provider for embeddings")
        return _create_openai_embedding_config(openai_key)

    # Fallback to Ollama
    logger.info("Using Ollama provider for embeddings (local service)")
    return _create_ollama_embedding_config()


def _create_deepinfra_embedding_config(api_token: str) -> EmbeddingConfig:
    """
    Create configuration for DeepInfra embedding provider.
    Default model: google/embeddinggemma-300m (768 dimensions)
    https://deepinfra.com/google/embeddinggemma-300m
    """
    model_name = os.environ.get("DEEPINFRA_EMBEDDING_MODEL", "google/embeddinggemma-300m")

    # Determine dimensions based on model
    # embeddinggemma-300m produces 768-dimensional embeddings
    dimensions = int(os.environ.get("DEEPINFRA_EMBEDDING_DIMENSIONS", "768"))

    return EmbeddingConfig(
        provider="deepinfra",
        base_url=os.environ.get("DEEPINFRA_EMBEDDING_BASE_URL", "https://api.deepinfra.com/v1/openai"),
        api_key=api_token,
        model_name=model_name,
        dimensions=dimensions,
        timeout=int(os.environ.get("DEEPINFRA_EMBEDDING_TIMEOUT", "360"))
    )


def _create_openai_embedding_config(api_key: str) -> EmbeddingConfig:
    """
    Create configuration for OpenAI embedding provider.
    Default model: text-embedding-ada-002 (1536 dimensions)
    """
    model_name = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")

    # Determine dimensions based on model
    # text-embedding-ada-002: 1536 dimensions
    # text-embedding-3-small: 1536 dimensions (configurable)
    # text-embedding-3-large: 3072 dimensions (configurable)
    dimension_map = {
        "text-embedding-ada-002": 1536,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
    }
    default_dimensions = dimension_map.get(model_name, 1536)
    dimensions = int(os.environ.get("OPENAI_EMBEDDING_DIMENSIONS", str(default_dimensions)))

    return EmbeddingConfig(
        provider="openai",
        base_url=os.environ.get("OPENAI_EMBEDDING_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_key=api_key,
        model_name=model_name,
        dimensions=dimensions,
        timeout=int(os.environ.get("OPENAI_EMBEDDING_TIMEOUT", "360"))
    )


def _create_ollama_embedding_config() -> EmbeddingConfig:
    """
    Create configuration for Ollama embedding provider (local service).
    Default model: mxbai-embed-large (1024 dimensions)
    """
    model_name = os.environ.get("OLLAMA_EMBEDDING_MODEL", "mxbai-embed-large")

    # Determine dimensions based on model
    # mxbai-embed-large: 1024 dimensions
    # nomic-embed-text: 768 dimensions
    # all-minilm: 384 dimensions
    dimension_map = {
        "mxbai-embed-large": 1024,
        "nomic-embed-text": 768,
        "all-minilm": 384,
    }
    default_dimensions = dimension_map.get(model_name, 1024)
    dimensions = int(os.environ.get("OLLAMA_EMBEDDING_DIMENSIONS", str(default_dimensions)))

    return EmbeddingConfig(
        provider="ollama",
        base_url=os.environ.get("OLLAMA_EMBEDDING_BASE_URL") or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.environ.get("OLLAMA_API_KEY", "openai_api_key"),  # Ollama doesn't require real key
        model_name=model_name,
        dimensions=dimensions,
        timeout=int(os.environ.get("OLLAMA_EMBEDDING_TIMEOUT", "360"))
    )