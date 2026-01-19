"""
Self-service usage data retrieval for authenticated users
Users can view their own usage data, graphs, and download CSV reports
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from api.models.usage_tracking import UsageLog, UsageSummary, UsageSummaryByModel, StorageUsage
from api.models.accounts import Account


class UsageService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_my_summary(
        self,
        account_id: int,
        start_date: date,
        end_date: date,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """
        Get usage summary for the authenticated user's account.

        Args:
            account_id: User's account ID (from JWT token)
            start_date: Start date for the report
            end_date: End date for the report
            group_by: Grouping interval ("day", "week", "month")

        Returns:
            Dictionary with account info and usage data
        """
        # Get account info
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return {
                "account_id": account_id,
                "account_name": "Unknown",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "group_by": group_by,
                "data": [],
                "total_records": 0
            }

        # Query usage summaries for this account
        summaries = self.db.query(UsageSummary).filter(
            and_(
                UsageSummary.account_id == account_id,
                UsageSummary.date >= start_date,
                UsageSummary.date <= end_date
            )
        ).order_by(UsageSummary.date).all()

        # Format data
        data = []
        for summary in summaries:
            data.append({
                "date": summary.date.isoformat(),
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
            "account_id": account_id,
            "account_name": account.name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "group_by": group_by,
            "data": data,
            "total_records": len(data)
        }

    def get_my_models(
        self,
        account_id: int,
        start_date: date,
        end_date: date,
        provider: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get model usage breakdown for the authenticated user's account.

        Args:
            account_id: User's account ID (from JWT token)
            start_date: Start date for the report
            end_date: End date for the report
            provider: Optional provider filter
            model_name: Optional model name filter

        Returns:
            Dictionary with account info and model usage data
        """
        # Get account info
        account = self.db.query(Account).filter(Account.id == account_id).first()

        # Build query
        query = self.db.query(UsageSummaryByModel).filter(
            and_(
                UsageSummaryByModel.account_id == account_id,
                UsageSummaryByModel.date >= start_date,
                UsageSummaryByModel.date <= end_date
            )
        )

        if provider:
            query = query.filter(UsageSummaryByModel.provider == provider)
        if model_name:
            query = query.filter(UsageSummaryByModel.model_name == model_name)

        summaries = query.order_by(UsageSummaryByModel.date).all()

        # Format data
        data = []
        for summary in summaries:
            data.append({
                "date": summary.date.isoformat(),
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
            "account_id": account_id,
            "account_name": account.name if account else "Unknown",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": data
        }

    def get_my_storage(
        self,
        account_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get storage usage for the authenticated user's account.

        Args:
            account_id: User's account ID (from JWT token)
            start_date: Start date for the report
            end_date: End date for the report

        Returns:
            Dictionary with account info and storage usage data
        """
        # Get account info
        account = self.db.query(Account).filter(Account.id == account_id).first()

        # Query storage usage
        storage = self.db.query(StorageUsage).filter(
            and_(
                StorageUsage.account_id == account_id,
                StorageUsage.date >= start_date,
                StorageUsage.date <= end_date
            )
        ).order_by(StorageUsage.date).all()

        # Format data
        data = []
        for s in storage:
            data.append({
                "date": s.date.isoformat(),
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
            "account_id": account_id,
            "account_name": account.name if account else "Unknown",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": data
        }
