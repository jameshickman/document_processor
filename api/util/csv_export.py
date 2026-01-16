"""
CSV export functionality for usage reports
"""

import csv
import io
from datetime import date
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException
from api.models import UsageSummary, UsageSummaryByModel, StorageUsage, Account, UsageLog


def export_usage_summary_csv(
    db: Session,
    start_date: date,
    end_date: date,
    account_id: int = None
) -> str:
    """
    Export usage summary data to CSV format.
    
    Args:
        db: Database session
        start_date: Start date for the report
        end_date: End date for the report
        account_id: Optional account ID to filter by
        
    Returns:
        CSV formatted string
    """
    query = db.query(UsageSummary).filter(
        and_(
            UsageSummary.date >= start_date,
            UsageSummary.date <= end_date
        )
    )

    if account_id:
        query = query.filter(UsageSummary.account_id == account_id)

    # Join with accounts to get account names
    query = query.join(Account, UsageSummary.account_id == Account.id)

    summaries = query.all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Date", "Account ID", "Account Name", "Total Operations", "Workbench Operations",
        "API Operations", "Extractions", "Classifications", "Total Tokens", "Input Tokens",
        "Output Tokens", "Successful", "Failed"
    ])

    # Write data rows
    for summary in summaries:
        writer.writerow([
            summary.date.isoformat(),
            summary.account_id,
            summary.account.name,
            summary.total_operations,
            summary.workbench_operations,
            summary.api_operations,
            summary.extractions,
            summary.classifications,
            summary.total_tokens or 0,
            summary.total_input_tokens or 0,
            summary.total_output_tokens or 0,
            summary.successful_operations,
            summary.failed_operations
        ])

    return output.getvalue()


def export_model_usage_csv(
    db: Session,
    start_date: date,
    end_date: date,
    account_id: int = None,
    provider: str = None,
    model_name: str = None
) -> str:
    """
    Export model usage data to CSV format.
    
    Args:
        db: Database session
        start_date: Start date for the report
        end_date: End date for the report
        account_id: Optional account ID to filter by
        provider: Optional provider to filter by
        model_name: Optional model name to filter by
        
    Returns:
        CSV formatted string
    """
    query = db.query(UsageSummaryByModel).filter(
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

    # Join with accounts to get account names
    query = query.join(Account, UsageSummaryByModel.account_id == Account.id)

    summaries = query.all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Date", "Account ID", "Account Name", "Provider", "Model Name", "Operation Count",
        "Input Tokens", "Output Tokens", "Total Tokens", "Avg Duration (ms)", "Successful", "Failed"
    ])

    # Write data rows
    for summary in summaries:
        writer.writerow([
            summary.date.isoformat(),
            summary.account_id,
            summary.account.name,
            summary.provider,
            summary.model_name,
            summary.operation_count,
            summary.input_tokens or 0,
            summary.output_tokens or 0,
            summary.total_tokens or 0,
            summary.avg_duration_ms or 0,
            summary.successful_operations,
            summary.failed_operations
        ])

    return output.getvalue()


def export_storage_usage_csv(
    db: Session,
    start_date: date,
    end_date: date,
    account_id: int = None
) -> str:
    """
    Export storage usage data to CSV format.
    
    Args:
        db: Database session
        start_date: Start date for the report
        end_date: End date for the report
        account_id: Optional account ID to filter by
        
    Returns:
        CSV formatted string
    """
    query = db.query(StorageUsage).filter(
        and_(
            StorageUsage.date >= start_date,
            StorageUsage.date <= end_date
        )
    )

    if account_id:
        query = query.filter(StorageUsage.account_id == account_id)

    # Join with accounts to get account names
    query = query.join(Account, StorageUsage.account_id == Account.id)

    storage_usages = query.all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Date", "Account ID", "Account Name", "Total Bytes", "Total GB", "Document Count",
        "Storage Backend", "PDF Bytes", "DOCX Bytes", "HTML Bytes", "Other Bytes"
    ])

    # Write data rows
    for usage in storage_usages:
        writer.writerow([
            usage.date.isoformat(),
            usage.account_id,
            usage.account.name,
            usage.total_bytes,
            round(usage.total_bytes / (1024**3), 2),
            usage.document_count,
            usage.storage_backend or "",
            usage.pdf_bytes or 0,
            usage.docx_bytes or 0,
            usage.html_bytes or 0,
            usage.other_bytes or 0
        ])

    return output.getvalue()


def export_event_logs_csv(
    db: Session,
    start_date: date,
    end_date: date,
    account_id: int = None,
    operation_type: str = None,
    source_type: str = None,
    status: str = None
) -> str:
    """
    Export event logs data to CSV format.
    
    Args:
        db: Database session
        start_date: Start date for the report
        end_date: End date for the report
        account_id: Optional account ID to filter by
        operation_type: Optional operation type to filter by
        source_type: Optional source type to filter by
        status: Optional status to filter by
        
    Returns:
        CSV formatted string
    """
    query = db.query(UsageLog).filter(
        and_(
            UsageLog.timestamp >= start_date,
            UsageLog.timestamp <= end_date
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

    # Join with accounts to get account names
    query = query.join(Account, UsageLog.account_id == Account.id)

    logs = query.order_by(UsageLog.timestamp.desc()).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "ID", "Timestamp", "Account ID", "Account Name", "Operation Type", "Source Type",
        "Document ID", "Extractor ID", "Classifier ID", "Provider", "Model Name",
        "Input Tokens", "Output Tokens", "Total Tokens", "Duration (ms)", "Status", "Error Message"
    ])

    # Write data rows
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.isoformat(),
            log.account_id,
            log.account.name,
            log.operation_type,
            log.source_type,
            log.document_id or "",
            log.extractor_id or "",
            log.classifier_id or "",
            log.provider or "",
            log.model_name or "",
            log.input_tokens or "",
            log.output_tokens or "",
            log.total_tokens or "",
            log.duration_ms or "",
            log.status,
            log.error_message or ""
        ])

    return output.getvalue()