"""
Metrics recorder protocol for dependency injection.

Defines the interface for recording LLM usage metrics.
Allows FactExtractor to be decoupled from specific telemetry implementations.
"""
from typing import Protocol, Optional


class MetricsRecorder(Protocol):
    """
    Protocol for recording LLM usage metrics.

    Implementations of this protocol can log to databases, metrics systems,
    or other telemetry backends.
    """

    def record_llm_call(
        self,
        operation_type: str,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Record an LLM API call with its metrics.

        Args:
            operation_type: Type of operation (e.g., 'extraction', 'embedding', 'classification')
            provider: LLM provider name (e.g., 'openai', 'deepinfra', 'ollama')
            model_name: Model identifier
            input_tokens: Number of input tokens (prompt)
            output_tokens: Number of output tokens (completion)
            duration_ms: Duration of the call in milliseconds
            status: Call status ('success', 'failure', 'partial')
            error_message: Error message if status is 'failure'
            **kwargs: Additional context (document_id, extractor_id, etc.)
        """
        ...


class NoOpMetricsRecorder:
    """
    No-op implementation that does nothing.

    Useful for testing or when metrics recording is disabled.
    """

    def record_llm_call(
        self,
        operation_type: str,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        **kwargs
    ) -> None:
        """No-op implementation."""
        pass
