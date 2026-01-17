"""
Usage tracking service for logging and aggregating usage metrics
"""

import time
from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from api.models.usage_tracking import UsageLog, UsageSummary, UsageSummaryByModel, StorageUsage


class UsageTracker:
    def __init__(self, db_session: Session):
        self.db = db_session

    def log_extraction_sync(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        extractor_id: Optional[int] = None,
        llm_model_id: Optional[int] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log an extraction operation (synchronous version)."""
        # Calculate total_tokens only if at least one is not None
        total_tokens = None
        if input_tokens is not None or output_tokens is not None:
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        usage_log = UsageLog(
            account_id=account_id,
            operation_type='extraction',
            source_type=source_type,
            document_id=document_id,
            extractor_id=extractor_id,
            llm_model_id=llm_model_id,
            provider=provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            user_agent=user_agent,
            ip_address=ip_address
        )

        self.db.add(usage_log)
        self.db.commit()

    def log_classification_sync(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        classifier_id: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log a classification operation (synchronous version)."""
        usage_log = UsageLog(
            account_id=account_id,
            operation_type='classification',
            source_type=source_type,
            document_id=document_id,
            classifier_id=classifier_id,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            user_agent=user_agent,
            ip_address=ip_address
        )

        self.db.add(usage_log)
        self.db.commit()

    def log_embedding_sync(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log an embedding operation (synchronous version)."""
        usage_log = UsageLog(
            account_id=account_id,
            operation_type='embedding',
            source_type=source_type,
            document_id=document_id,
            provider=provider,
            model_name=model_name,
            input_tokens=input_tokens,
            total_tokens=input_tokens,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            user_agent=user_agent,
            ip_address=ip_address
        )

        self.db.add(usage_log)
        self.db.commit()

    def log_upload_sync(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        bytes_stored: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log a document upload operation (synchronous version)."""
        usage_log = UsageLog(
            account_id=account_id,
            operation_type='upload',
            source_type=source_type,
            document_id=document_id,
            bytes_stored=bytes_stored,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            user_agent=user_agent,
            ip_address=ip_address
        )

        self.db.add(usage_log)
        self.db.commit()

    async def log_extraction(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        extractor_id: Optional[int] = None,
        llm_model_id: Optional[int] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log an extraction operation."""
        # Just call the sync version for now
        self.log_extraction_sync(
            account_id=account_id,
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
            source_type=source_type,
            user_agent=user_agent,
            ip_address=ip_address
        )

    async def log_classification(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        classifier_id: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log a classification operation."""
        # Just call the sync version for now
        self.log_classification_sync(
            account_id=account_id,
            document_id=document_id,
            classifier_id=classifier_id,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            source_type=source_type,
            user_agent=user_agent,
            ip_address=ip_address
        )

    async def log_embedding(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        input_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log an embedding operation."""
        # Just call the sync version for now
        self.log_embedding_sync(
            account_id=account_id,
            document_id=document_id,
            provider=provider,
            model_name=model_name,
            input_tokens=input_tokens,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            source_type=source_type,
            user_agent=user_agent,
            ip_address=ip_address
        )

    async def log_upload(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        bytes_stored: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log a document upload operation."""
        # Just call the sync version for now
        self.log_upload_sync(
            account_id=account_id,
            document_id=document_id,
            bytes_stored=bytes_stored,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            source_type=source_type,
            user_agent=user_agent,
            ip_address=ip_address
        )

    def log_download_sync(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log a document download operation (synchronous version)."""
        usage_log = UsageLog(
            account_id=account_id,
            operation_type='download',
            source_type=source_type,
            document_id=document_id,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            user_agent=user_agent,
            ip_address=ip_address
        )

        self.db.add(usage_log)
        self.db.commit()

    async def log_download(
        self,
        account_id: int,
        document_id: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        source_type: str = 'workbench',
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log a document download operation."""
        # Just call the sync version for now
        self.log_download_sync(
            account_id=account_id,
            document_id=document_id,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            source_type=source_type,
            user_agent=user_agent,
            ip_address=ip_address
        )

    async def aggregate_daily_usage(self, target_date: date):
        """
        Aggregate usage logs for a specific date into daily summaries.
        This should be called by a background job.
        """
        # First, delete any existing summaries for this date to avoid duplicates
        self.db.query(UsageSummary).filter(UsageSummary.date == target_date).delete()
        self.db.query(UsageSummaryByModel).filter(UsageSummaryByModel.date == target_date).delete()
        
        # Aggregate by account and operation type
        daily_stats = self.db.query(
            UsageLog.account_id,
            UsageLog.operation_type,
            UsageLog.source_type,
            UsageLog.provider,
            UsageLog.model_name,
            func.count(UsageLog.id).label('count'),
            func.sum(UsageLog.input_tokens).label('total_input_tokens'),
            func.sum(UsageLog.output_tokens).label('total_output_tokens'),
            func.sum(UsageLog.total_tokens).label('total_tokens'),
            func.sum(UsageLog.bytes_stored).label('total_bytes_stored'),
            func.avg(UsageLog.duration_ms).label('avg_duration_ms'),
            func.sum(case((UsageLog.status == 'success', 1), else_=0)).label('successful_ops'),
            func.sum(case((UsageLog.status != 'success', 1), else_=0)).label('failed_ops')
        ).filter(
            func.date(UsageLog.timestamp) == target_date
        ).group_by(
            UsageLog.account_id,
            UsageLog.operation_type,
            UsageLog.source_type,
            UsageLog.provider,
            UsageLog.model_name
        ).all()

        # Organize data by account for summary aggregation
        account_data = {}
        model_data = {}

        for stat in daily_stats:
            account_id = stat.account_id
            
            # Initialize account data if not present
            if account_id not in account_data:
                account_data[account_id] = {
                    'workbench_operations': 0,
                    'api_operations': 0,
                    'extractions': 0,
                    'classifications': 0,
                    'embeddings': 0,
                    'uploads': 0,
                    'downloads': 0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_tokens': 0,
                    'bytes_uploaded': 0,
                    'successful_operations': 0,
                    'failed_operations': 0,
                    'total_operations': 0,
                    'duration_total': 0,
                    'operation_count': 0
                }
            
            # Update account summary
            account_data[account_id]['total_operations'] += stat.count
            if stat.source_type == 'workbench':
                account_data[account_id]['workbench_operations'] += stat.count
            elif stat.source_type == 'api':
                account_data[account_id]['api_operations'] += stat.count
                
            if stat.operation_type == 'extraction':
                account_data[account_id]['extractions'] += stat.count
            elif stat.operation_type == 'classification':
                account_data[account_id]['classifications'] += stat.count
            elif stat.operation_type == 'embedding':
                account_data[account_id]['embeddings'] += stat.count
            elif stat.operation_type == 'upload':
                account_data[account_id]['uploads'] += stat.count
            elif stat.operation_type == 'download':
                account_data[account_id]['downloads'] += stat.count
                
            account_data[account_id]['total_input_tokens'] += (stat.total_input_tokens or 0)
            account_data[account_id]['total_output_tokens'] += (stat.total_output_tokens or 0)
            account_data[account_id]['total_tokens'] += (stat.total_tokens or 0)
            account_data[account_id]['bytes_uploaded'] += (stat.total_bytes_stored or 0)
            account_data[account_id]['successful_operations'] += stat.successful_ops
            account_data[account_id]['failed_operations'] += stat.failed_ops
            account_data[account_id]['duration_total'] += (stat.avg_duration_ms or 0) * stat.count
            account_data[account_id]['operation_count'] += stat.count
        
        # Create usage summaries
        for account_id, data in account_data.items():
            avg_duration = int(data['duration_total'] / data['operation_count']) if data['operation_count'] > 0 else None
            
            summary = UsageSummary(
                account_id=account_id,
                date=target_date,
                workbench_operations=data['workbench_operations'],
                api_operations=data['api_operations'],
                total_operations=data['total_operations'],
                extractions=data['extractions'],
                classifications=data['classifications'],
                embeddings=data['embeddings'],
                uploads=data['uploads'],
                downloads=data['downloads'],
                total_input_tokens=data['total_input_tokens'],
                total_output_tokens=data['total_output_tokens'],
                total_tokens=data['total_tokens'],
                successful_operations=data['successful_operations'],
                failed_operations=data['failed_operations'],
                bytes_uploaded=data['bytes_uploaded'],
                avg_duration_ms=avg_duration
            )
            self.db.add(summary)
        
        # Create model-specific summaries
        for stat in daily_stats:
            if stat.provider and stat.model_name:  # Only create model summaries for LLM operations
                key = (stat.account_id, stat.provider, stat.model_name)
                
                if key not in model_data:
                    model_data[key] = {
                        'operation_count': 0,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'total_tokens': 0,
                        'successful_operations': 0,
                        'failed_operations': 0,
                        'duration_total': 0,
                        'operation_count_for_avg': 0
                    }
                
                model_data[key]['operation_count'] += stat.count
                model_data[key]['input_tokens'] += (stat.total_input_tokens or 0)
                model_data[key]['output_tokens'] += (stat.total_output_tokens or 0)
                model_data[key]['total_tokens'] += (stat.total_tokens or 0)
                model_data[key]['successful_operations'] += stat.successful_ops
                model_data[key]['failed_operations'] += stat.failed_ops
                model_data[key]['duration_total'] += (stat.avg_duration_ms or 0) * stat.count
                model_data[key]['operation_count_for_avg'] += stat.count
        
        for (account_id, provider, model_name), data in model_data.items():
            avg_duration = int(data['duration_total'] / data['operation_count_for_avg']) if data['operation_count_for_avg'] > 0 else None
            
            model_summary = UsageSummaryByModel(
                account_id=account_id,
                date=target_date,
                provider=provider,
                model_name=model_name,
                operation_count=data['operation_count'],
                input_tokens=data['input_tokens'],
                output_tokens=data['output_tokens'],
                total_tokens=data['total_tokens'],
                successful_operations=data['successful_operations'],
                failed_operations=data['failed_operations'],
                avg_duration_ms=avg_duration
            )
            self.db.add(model_summary)
        
        self.db.commit()

    async def calculate_storage_usage(self, target_date: date):
        """
        Calculate storage usage for all accounts on a specific date.
        This should be called by a background job.
        """
        # First, delete any existing storage usage for this date to avoid duplicates
        self.db.query(StorageUsage).filter(StorageUsage.date == target_date).delete()
        
        # Get document sizes grouped by account
        storage_stats = self.db.query(
            UsageLog.account_id,
            func.sum(UsageLog.bytes_stored).label('total_bytes'),
            func.count(UsageLog.document_id).label('document_count')
        ).filter(
            and_(
                func.date(UsageLog.timestamp) <= target_date,
                UsageLog.operation_type == 'upload',
                UsageLog.status == 'success'
            )
        ).group_by(
            UsageLog.account_id
        ).all()
        
        for stat in storage_stats:
            storage_usage = StorageUsage(
                account_id=stat.account_id,
                date=target_date,
                total_bytes=stat.total_bytes or 0,
                document_count=stat.document_count or 0
            )
            self.db.add(storage_usage)
        
        self.db.commit()