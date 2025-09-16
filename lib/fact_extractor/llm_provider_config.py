import os
import logging
from typing import Optional, Dict, Any
from lib.fact_extractor.models import LLMConfig

logger = logging.getLogger(__name__)

# Check if DeepInfra is available
try:
    from langchain_community.llms import DeepInfra
    DEEPINFRA_AVAILABLE = True
except ImportError:
    DEEPINFRA_AVAILABLE = False


def create_llm_config() -> LLMConfig:
    """
    Create LLM configuration with fallback priority:
    1. DeepInfra (if DEEPINFRA_API_TOKEN is set and package available)
    2. OpenAI (if OPENAI_API_KEY is set)
    3. Ollama (local service fallback)
    """
    
    # Check for DeepInfra configuration first
    deepinfra_token = os.environ.get("DEEPINFRA_API_TOKEN")
    if deepinfra_token:
        if DEEPINFRA_AVAILABLE:
            logger.info("Using DeepInfra provider")
            return _create_deepinfra_config(deepinfra_token)
        else:
            logger.warning("DEEPINFRA_API_TOKEN found but langchain-community not installed, using OpenAI-compatible fallback")
            return _create_deepinfra_fallback_config(deepinfra_token)
    
    # Check for OpenAI configuration
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key and openai_key != "openai_api_key":  # Exclude default placeholder
        logger.info("Using OpenAI provider")
        return _create_openai_config(openai_key)
    
    # Fallback to Ollama
    logger.info("Using Ollama provider (local service)")
    return _create_ollama_config()


def _create_deepinfra_config(api_token: str) -> LLMConfig:
    """Create configuration for DeepInfra provider."""
    model_kwargs = {
        "temperature": float(os.environ.get("DEEPINFRA_TEMPERATURE", "0")),
        "repetition_penalty": float(os.environ.get("DEEPINFRA_REPETITION_PENALTY", "1.2")),
        "max_new_tokens": int(os.environ.get("DEEPINFRA_MAX_NEW_TOKENS", "250")),
        "top_p": float(os.environ.get("DEEPINFRA_TOP_P", "0.9")),
    }
    
    return LLMConfig(
        provider="deepinfra",
        base_url="",  # DeepInfra uses its own endpoint
        api_key=api_token,
        model_name=os.environ.get("DEEPINFRA_MODEL_NAME", "meta-llama/Llama-2-70b-chat-hf"),
        temperature=model_kwargs["temperature"],
        max_tokens=model_kwargs["max_new_tokens"],
        timeout=int(os.environ.get("DEEPINFRA_TIMEOUT", "360")),
        model_kwargs=model_kwargs
    )


def _create_deepinfra_fallback_config(api_token: str) -> LLMConfig:
    """Create fallback configuration for DeepInfra using OpenAI-compatible API."""
    return LLMConfig(
        provider="deepinfra",
        base_url="https://api.deepinfra.com/v1/openai",
        api_key=api_token,
        model_name=os.environ.get("DEEPINFRA_MODEL_NAME", "meta-llama/Llama-2-70b-chat-hf"),
        temperature=float(os.environ.get("DEEPINFRA_TEMPERATURE", "0.7")),
        max_tokens=int(os.environ.get("DEEPINFRA_MAX_NEW_TOKENS", "250")),
        timeout=int(os.environ.get("DEEPINFRA_TIMEOUT", "360")),
    )


def _create_openai_config(api_key: str) -> LLMConfig:
    """Create configuration for OpenAI provider."""
    return LLMConfig(
        provider="openai",
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        api_key=api_key,
        model_name=os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo"),
        temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.05")),
        max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "2048")),
        timeout=int(os.environ.get("OPENAI_TIMEOUT", "360")),
    )


def _create_ollama_config() -> LLMConfig:
    """Create configuration for Ollama provider (local service)."""
    return LLMConfig(
        provider="ollama",
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.environ.get("OLLAMA_API_KEY", "openai_api_key"),  # Ollama doesn't require real key
        model_name=os.environ.get("OLLAMA_MODEL_NAME", "gemma3n"),
        temperature=float(os.environ.get("OLLAMA_TEMPERATURE", "0.05")),
        max_tokens=int(os.environ.get("OLLAMA_MAX_TOKENS", "2048")),
        timeout=int(os.environ.get("OLLAMA_TIMEOUT", "360")),
    )