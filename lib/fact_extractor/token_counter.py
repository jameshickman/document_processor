"""
Token counting utilities with fallback estimation.

Provides accurate token counting when available (via tiktoken),
with word-based estimation as a fallback.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.debug("tiktoken not available, will use word-based estimation")


class TokenCounter:
    """
    Token counter with multiple strategies:
    1. Exact counting using tiktoken (when available)
    2. Word-based estimation (fallback)
    """

    # Token-to-word ratio estimates for different scenarios
    # Based on empirical observations: English text averages ~1.3 tokens per word
    DEFAULT_TOKEN_MULTIPLIER = 1.3

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize token counter.

        Args:
            model_name: Model name for tiktoken encoding (e.g., "gpt-3.5-turbo", "gpt-4")
        """
        self.model_name = model_name
        self.encoder = None

        if TIKTOKEN_AVAILABLE and model_name:
            try:
                # Try to get encoding for the specific model
                self.encoder = tiktoken.encoding_for_model(model_name)
                logger.debug(f"Initialized tiktoken encoder for model: {model_name}")
            except KeyError:
                # Model not found, try common encodings
                try:
                    # cl100k_base is used by gpt-4, gpt-3.5-turbo, text-embedding-ada-002
                    self.encoder = tiktoken.get_encoding("cl100k_base")
                    logger.debug(f"Model {model_name} not found, using cl100k_base encoding")
                except Exception as e:
                    logger.warning(f"Failed to initialize tiktoken encoder: {e}")
                    self.encoder = None

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using best available method.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated number of tokens
        """
        if not text:
            return 0

        # Try exact counting first
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                logger.warning(f"Tiktoken encoding failed: {e}, falling back to estimation")

        # Fallback to word-based estimation
        return self.estimate_tokens_from_words(text)

    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text.

        Args:
            text: Text to count words in

        Returns:
            Number of words
        """
        if not text:
            return 0
        return len(text.split())

    @classmethod
    def estimate_tokens_from_words(cls, text: str) -> int:
        """
        Estimate token count from word count.

        Uses empirical multiplier of 1.3 tokens per word for English text.
        This is a reasonable estimate when exact token counting is unavailable.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated number of tokens
        """
        word_count = cls.count_words(text)
        return int(word_count * cls.DEFAULT_TOKEN_MULTIPLIER)

    @staticmethod
    def estimate_tokens_from_word_count(word_count: int) -> int:
        """
        Estimate token count from a known word count.

        Args:
            word_count: Number of words

        Returns:
            Estimated number of tokens
        """
        return int(word_count * TokenCounter.DEFAULT_TOKEN_MULTIPLIER)
