import os
from lib.fact_extractor.models import LLMConfig

llm_config = LLMConfig(
    base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "openai_api_key"),
    model_name=os.environ.get("OPENAI_MODEL_NAME", "gemma3n"), # gpt-4
    temperature=float(os.environ.get("OPENAI_TEMPERATURE", 0.05)),
    max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", 2048)),
    timeout=int(os.environ.get("OPENAI_TIMEOUT", 360)),
)