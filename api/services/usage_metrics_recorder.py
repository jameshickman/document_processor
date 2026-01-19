"""
UsageTracker adapter that implements the MetricsRecorder protocol.

Allows FactExtractor to record metrics through dependency injection
while maintaining backward compatibility with the existing UsageTracker.
"""
from typing import Optional
from sqlalchemy.orm import Session
from api.services.usage_tracker import UsageTracker


class UsageMetricsRecorder:
    """
    Adapter that implements MetricsRecorder protocol using UsageTracker.

    This allows FactExtractor to record usage metrics without being
    directly coupled to the UsageTracker implementation.
    """

    def __init__(
        self,
        db_session: Session,
        account_id: int,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Initialize the metrics recorder.

        Args:
            db_session: Database session for logging
            account_id: Account ID for usage tracking
            source_type: Source type ('workbench' or 'api')
            user_agent: User agent string
            ip_address: IP address
        """
        self.tracker = UsageTracker(db_session)
        self.account_id = account_id
        self.source_type = source_type
        self.user_agent = user_agent
        self.ip_address = ip_address

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
            operation_type: Type of operation (e.g., 'extraction', 'embedding')
            provider: LLM provider name
            model_name: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            duration_ms: Duration in milliseconds
            status: Call status
            error_message: Error message if failed
            **kwargs: Additional context (document_id, extractor_id, etc.)
        """
        # Extract additional context from kwargs
        document_id = kwargs.get('document_id')
        extractor_id = kwargs.get('extractor_id')
        llm_model_id = kwargs.get('llm_model_id')

        # Map operation_type to the appropriate logging method
        if operation_type == 'extraction':
            self.tracker.log_extraction_sync(
                account_id=self.account_id,
                document_id=document_id,
                extractor_id=extractor_id,
                llm_model_id=llm_model_id,
                provider=provider,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                status=status,
                error_message=error_message,
                source_type=self.source_type,
                user_agent=self.user_agent,
                ip_address=self.ip_address
            )
        elif operation_type == 'embedding':
            self.tracker.log_embedding_sync(
                account_id=self.account_id,
                document_id=document_id,
                provider=provider,
                model_name=model_name,
                input_tokens=input_tokens,
                duration_ms=duration_ms,
                status=status,
                error_message=error_message,
                source_type=self.source_type,
                user_agent=self.user_agent,
                ip_address=self.ip_address
            )
        # Add other operation types as needed
