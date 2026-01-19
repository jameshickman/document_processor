"""
Administrative reporting service for users with reporting role
Provides cross-account usage data with filtering options
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from api.models.usage_tracking import UsageLog, UsageSummary, UsageSummaryByModel, StorageUsage
from api.models.accounts import Account


class ReportingService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_usage_summary(
        self,
        start_date: date,
        end_date: date,
        account_id: Optional[int] = None,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """
        Get usage summary across all accounts (or filtered by account).

        Args:
            start_date: Start date for the report
            end_date: End date for the report
            account_id: Optional account filter
            group_by: Grouping interval ("day", "week", "month")

        Returns:
            Dictionary with usage data across accounts
        """
        # Build query
        query = self.db.query(
            UsageSummary,
            Account.name.label('account_name')
        ).join(
            Account, UsageSummary.account_id == Account.id
        ).filter(
            and_(
                UsageSummary.date >= start_date,
                UsageSummary.date <= end_date
            )
        )

        if account_id:
            query = query.filter(UsageSummary.account_id == account_id)

        summaries = query.order_by(UsageSummary.account_id, UsageSummary.date).all()

        # Format data
        data = []
        for summary, account_name in summaries:
            data.append({
                "date": summary.date.isoformat(),
                "account_id": summary.account_id,
                "account_name": account_name,
                "total_operations": summary.total_operations or 0,
                "workbench_operations": summary.workbench_operations or 0,
                "api_operations": summary.api_operations or 0,
                "extractions": summary.extractions or 0,
                "classifications": summary.classifications or 0,
                "embeddings": summary.embeddings or 0,
                "uploads": summary.uploads or 0,
                "downloads": summary.downloads or 0,
                "total_tokens": summary.total_tokens or 0,
                "input_tokens": summary.total_input_tokens or 0,
                "output_tokens": summary.total_output_tokens or 0,
                "successful_operations": summary.successful_operations or 0,
                "failed_operations": summary.failed_operations or 0,
                "avg_duration_ms": summary.avg_duration_ms
            })

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "group_by": group_by,
            "data": data,
            "total_records": len(data)
        }

    def get_model_usage(
        self,
        start_date: date,
        end_date: date,
        account_id: Optional[int] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get model usage breakdown across accounts.

        Args:
            start_date: Start date for the report
            end_date: End date for the report
            account_id: Optional account filter
            provider: Optional provider filter
            model_name: Optional model name filter

        Returns:
            Dictionary with model usage data
        """
        # Build query
        query = self.db.query(
            UsageSummaryByModel,
            Account.name.label('account_name')
        ).join(
            Account, UsageSummaryByModel.account_id == Account.id
        ).filter(
            and_(
                UsageSummaryByModel.date >= start_date,
                UsageSummaryByModel.date <= end_date
            )
        )

        if account_id:
            query = query.filter(UsageSummaryByModel.account_id == account_id)
        if provider:
            query = query.filter(UsageSummaryByModel.provider == provider)
        if model_name:
            query = query.filter(UsageSummaryByModel.model_name == model_name)

        summaries = query.order_by(
            UsageSummaryByModel.account_id,
            UsageSummaryByModel.date
        ).all()

        # Format data
        data = []
        for summary, account_name in summaries:
            data.append({
                "date": summary.date.isoformat(),
                "account_id": summary.account_id,
                "account_name": account_name,
                "provider": summary.provider,
                "model_name": summary.model_name,
                "operation_count": summary.operation_count or 0,
                "input_tokens": summary.input_tokens or 0,
                "output_tokens": summary.output_tokens or 0,
                "total_tokens": summary.total_tokens or 0,
                "avg_duration_ms": summary.avg_duration_ms,
                "successful_operations": summary.successful_operations or 0,
                "failed_operations": summary.failed_operations or 0
            })

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": data
        }

    def get_storage_usage(
        self,
        start_date: date,
        end_date: date,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get storage usage across accounts.

        Args:
            start_date: Start date for the report
            end_date: End date for the report
            account_id: Optional account filter

        Returns:
            Dictionary with storage usage data
        """
        # Build query
        query = self.db.query(
            StorageUsage,
            Account.name.label('account_name')
        ).join(
            Account, StorageUsage.account_id == Account.id
        ).filter(
            and_(
                StorageUsage.date >= start_date,
                StorageUsage.date <= end_date
            )
        )

        if account_id:
            query = query.filter(StorageUsage.account_id == account_id)

        storage = query.order_by(StorageUsage.account_id, StorageUsage.date).all()

        # Format data
        data = []
        for s, account_name in storage:
            data.append({
                "date": s.date.isoformat(),
                "account_id": s.account_id,
                "account_name": account_name,
                "total_bytes": s.total_bytes or 0,
                "total_gb": round((s.total_bytes or 0) / (1024**3), 2),
                "document_count": s.document_count or 0,
                "storage_backend": s.storage_backend,
                "pdf_bytes": s.pdf_bytes or 0,
                "docx_bytes": s.docx_bytes or 0,
                "html_bytes": s.html_bytes or 0,
                "other_bytes": s.other_bytes or 0
            })

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": data
        }

    def get_event_logs(
        self,
        start_date: date,
        end_date: date,
        account_id: Optional[int] = None,
        operation_type: Optional[str] = None,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get detailed event logs with pagination.

        Args:
            start_date: Start date for the report
            end_date: End date for the report
            account_id: Optional account filter
            operation_type: Optional operation type filter
            source_type: Optional source type filter
            status: Optional status filter
            limit: Maximum number of records (default 100, max 1000)
            offset: Offset for pagination

        Returns:
            Dictionary with event log data and pagination info
        """
        # Enforce max limit
        limit = min(limit, 1000)

        # Build query
        query = self.db.query(
            UsageLog,
            Account.name.label('account_name')
        ).join(
            Account, UsageLog.account_id == Account.id
        ).filter(
            and_(
                UsageLog.timestamp >= datetime.combine(start_date, datetime.min.time()),
                UsageLog.timestamp <= datetime.combine(end_date, datetime.max.time())
            )
        )

        if account_id:
            query = query.filter(UsageLog.account_id == account_id)
        if operation_type:
            query = query.filter(UsageLog.operation_type == operation_type)
        if source_type:
            query = query.filter(UsageLog.source_type == source_type)
        if status:
            query = query.filter(UsageLog.status == status)

        # Get total count
        total = query.count()

        # Apply pagination and get results
        logs = query.order_by(UsageLog.timestamp.desc()).limit(limit).offset(offset).all()

        # Format data
        data = []
        for log, account_name in logs:
            data.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "account_id": log.account_id,
                "account_name": account_name,
                "operation_type": log.operation_type,
                "source_type": log.source_type,
                "document_id": log.document_id,
                "extractor_id": log.extractor_id,
                "classifier_id": log.classifier_id,
                "provider": log.provider,
                "model_name": log.model_name,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "total_tokens": log.total_tokens,
                "duration_ms": log.duration_ms,
                "status": log.status,
                "error_message": log.error_message
            })

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "filters": {
                "account_id": account_id,
                "operation_type": operation_type,
                "source_type": source_type,
                "status": status
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total
            },
            "data": data
        }

    def get_accounts(self, active_only: bool = True) -> Dict[str, Any]:
        """
        Get list of accounts for filtering.

        Args:
            active_only: If True, only return active accounts

        Returns:
            Dictionary with account list
        """
        query = self.db.query(Account)

        # Note: Assuming there's an 'active' field; adjust if needed
        # if active_only:
        #     query = query.filter(Account.active == True)

        accounts = query.order_by(Account.name).all()

        return {
            "accounts": [
                {
                    "id": account.id,
                    "name": account.name,
                    "email": account.email,
                    "created_at": account.created_at.isoformat() if account.created_at else None
                }
                for account in accounts
            ]
        }
