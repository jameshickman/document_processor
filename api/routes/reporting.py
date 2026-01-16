from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from datetime import datetime, date
from api.models.database import get_db
from api.rbac import require_roles_dependency
from api.models import UsageSummary, UsageSummaryByModel, StorageUsage, Account, UsageLog
from pydantic import BaseModel
from api.util.csv_export import (
    export_usage_summary_csv,
    export_model_usage_csv,
    export_storage_usage_csv,
    export_event_logs_csv
)

router = APIRouter()


class UsageSummaryItem(BaseModel):
    date: str
    account_id: int
    account_name: str
    total_operations: int
    workbench_operations: int
    api_operations: int
    extractions: int
    classifications: int
    total_tokens: int
    input_tokens: int
    output_tokens: int
    successful_operations: int
    failed_operations: int


class UsageSummaryResponse(BaseModel):
    start_date: str
    end_date: str
    group_by: str
    data: List[UsageSummaryItem]
    total_records: int


class ModelUsageItem(BaseModel):
    date: str
    account_id: int
    account_name: str
    provider: str
    model_name: str
    operation_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    avg_duration_ms: Optional[int]
    successful_operations: int
    failed_operations: int


class ModelUsageResponse(BaseModel):
    start_date: str
    end_date: str
    data: List[ModelUsageItem]


class StorageUsageItem(BaseModel):
    date: str
    account_id: int
    account_name: str
    total_bytes: int
    total_gb: float
    document_count: int
    storage_backend: Optional[str]
    pdf_bytes: int
    docx_bytes: int
    html_bytes: int
    other_bytes: int


class StorageUsageResponse(BaseModel):
    start_date: str
    end_date: str
    data: List[StorageUsageItem]


class EventLogItem(BaseModel):
    id: int
    timestamp: str
    account_id: int
    account_name: str
    operation_type: str
    source_type: str
    document_id: Optional[int]
    extractor_id: Optional[int]
    classifier_id: Optional[int]
    provider: Optional[str]
    model_name: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    duration_ms: Optional[int]
    status: str


class EventLogsResponse(BaseModel):
    start_date: str
    end_date: str
    filters: dict
    pagination: dict
    data: List[EventLogItem]


class AccountInfo(BaseModel):
    id: int
    name: str
    email: str
    active: bool
    created_at: str


class AccountsResponse(BaseModel):
    accounts: List[AccountInfo]


@router.get("/usage/summary", response_model=UsageSummaryResponse)
def get_usage_summary(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    account_id: Optional[int] = Query(None, description="Filter by specific account ID"),
    group_by: str = Query("day", description="Group by 'day', 'week', or 'month'"),
    db: Session = Depends(get_db),
    _: None = Depends(require_roles_dependency(["reporting", "admin"]))
):
    """
    Get usage summary aggregated by date range.
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

    # Convert to response format
    data = []
    for summary in summaries:
        data.append(UsageSummaryItem(
            date=summary.date.isoformat(),
            account_id=summary.account_id,
            account_name=summary.account.name,
            total_operations=summary.total_operations,
            workbench_operations=summary.workbench_operations,
            api_operations=summary.api_operations,
            extractions=summary.extractions,
            classifications=summary.classifications,
            total_tokens=summary.total_tokens or 0,
            input_tokens=summary.total_input_tokens or 0,
            output_tokens=summary.total_output_tokens or 0,
            successful_operations=summary.successful_operations,
            failed_operations=summary.failed_operations
        ))

    return UsageSummaryResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        group_by=group_by,
        data=data,
        total_records=len(data)
    )


@router.get("/usage/by-model", response_model=ModelUsageResponse)
def get_model_usage(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    account_id: Optional[int] = Query(None, description="Filter by specific account ID"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    db: Session = Depends(get_db),
    _: None = Depends(require_roles_dependency(["reporting", "admin"]))
):
    """
    Get usage breakdown by model.
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

    # Convert to response format
    data = []
    for summary in summaries:
        data.append(ModelUsageItem(
            date=summary.date.isoformat(),
            account_id=summary.account_id,
            account_name=summary.account.name,
            provider=summary.provider,
            model_name=summary.model_name,
            operation_count=summary.operation_count,
            input_tokens=summary.input_tokens or 0,
            output_tokens=summary.output_tokens or 0,
            total_tokens=summary.total_tokens or 0,
            avg_duration_ms=summary.avg_duration_ms,
            successful_operations=summary.successful_operations,
            failed_operations=summary.failed_operations
        ))

    return ModelUsageResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        data=data
    )


@router.get("/storage", response_model=StorageUsageResponse)
def get_storage_usage(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    account_id: Optional[int] = Query(None, description="Filter by specific account ID"),
    db: Session = Depends(get_db),
    _: None = Depends(require_roles_dependency(["reporting", "admin"]))
):
    """
    Get storage usage by date range.
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

    # Convert to response format
    data = []
    for usage in storage_usages:
        data.append(StorageUsageItem(
            date=usage.date.isoformat(),
            account_id=usage.account_id,
            account_name=usage.account.name,
            total_bytes=usage.total_bytes,
            total_gb=round(usage.total_bytes / (1024**3), 2),
            document_count=usage.document_count,
            storage_backend=usage.storage_backend,
            pdf_bytes=usage.pdf_bytes or 0,
            docx_bytes=usage.docx_bytes or 0,
            html_bytes=usage.html_bytes or 0,
            other_bytes=usage.other_bytes or 0
        ))

    return StorageUsageResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        data=data
    )


@router.get("/logs", response_model=EventLogsResponse)
def get_event_logs(
    start_date: datetime = Query(..., description="Start date and time (YYYY-MM-DDTHH:MM:SS)"),
    end_date: datetime = Query(..., description="End date and time (YYYY-MM-DDTHH:MM:SS)"),
    account_id: Optional[int] = Query(None, description="Filter by specific account ID"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    _: None = Depends(require_roles_dependency(["reporting", "admin"]))
):
    """
    Get raw usage event logs.
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

    # Apply pagination
    logs = query.order_by(UsageLog.timestamp.desc()).offset(offset).limit(limit).all()

    # Count total records for pagination info
    total_query = db.query(func.count(UsageLog.id)).filter(
        and_(
            UsageLog.timestamp >= start_date,
            UsageLog.timestamp <= end_date
        )
    )
    if account_id:
        total_query = total_query.filter(UsageLog.account_id == account_id)
    if operation_type:
        total_query = total_query.filter(UsageLog.operation_type == operation_type)
    if source_type:
        total_query = total_query.filter(UsageLog.source_type == source_type)
    if status:
        total_query = total_query.filter(UsageLog.status == status)

    total_count = total_query.scalar()

    # Convert to response format
    data = []
    for log in logs:
        data.append(EventLogItem(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            account_id=log.account_id,
            account_name=log.account.name,
            operation_type=log.operation_type,
            source_type=log.source_type,
            document_id=log.document_id,
            extractor_id=log.extractor_id,
            classifier_id=log.classifier_id,
            provider=log.provider,
            model_name=log.model_name,
            input_tokens=log.input_tokens,
            output_tokens=log.output_tokens,
            total_tokens=log.total_tokens,
            duration_ms=log.duration_ms,
            status=log.status
        ))

    return EventLogsResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        filters={
            "account_id": account_id,
            "operation_type": operation_type,
            "source_type": source_type,
            "status": status
        },
        pagination={
            "limit": limit,
            "offset": offset,
            "total": total_count
        },
        data=data
    )


@router.get("/accounts", response_model=AccountsResponse)
def get_accounts(
    active_only: bool = Query(True, description="Return only active accounts"),
    db: Session = Depends(get_db),
    _: None = Depends(require_roles_dependency(["reporting", "admin"]))
):
    """
    Get list of accounts for reporting purposes.
    """
    query = db.query(Account)

    if active_only:
        query = query.filter(Account.active == True)

    accounts = query.all()

    # Convert to response format
    data = []
    for account in accounts:
        data.append(AccountInfo(
            id=account.id,
            name=account.name,
            email=account.email,
            active=account.active,
            created_at=account.time_created.isoformat() if account.time_created else None
        ))

    return AccountsResponse(accounts=data)


@router.get("/export/csv")
def export_csv(
    report_type: str = Query(..., description="Type of report to export: 'summary', 'by_model', 'storage', or 'logs'"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    account_id: Optional[int] = Query(None, description="Filter by specific account ID"),
    provider: Optional[str] = Query(None, description="Filter by provider (for model usage)"),
    model_name: Optional[str] = Query(None, description="Filter by model name (for model usage)"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type (for logs)"),
    source_type: Optional[str] = Query(None, description="Filter by source type (for logs)"),
    status: Optional[str] = Query(None, description="Filter by status (for logs)"),
    db: Session = Depends(get_db),
    _: None = Depends(require_roles_dependency(["reporting", "admin"]))
):
    """
    Export usage data to CSV format.
    """
    if report_type == "summary":
        csv_content = export_usage_summary_csv(
            db=db,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id
        )
        filename = f"usage_summary_{start_date}_{end_date}.csv"
    elif report_type == "by_model":
        csv_content = export_model_usage_csv(
            db=db,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            provider=provider,
            model_name=model_name
        )
        filename = f"model_usage_{start_date}_{end_date}.csv"
    elif report_type == "storage":
        csv_content = export_storage_usage_csv(
            db=db,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id
        )
        filename = f"storage_usage_{start_date}_{end_date}.csv"
    elif report_type == "logs":
        csv_content = export_event_logs_csv(
            db=db,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            operation_type=operation_type,
            source_type=source_type,
            status=status
        )
        filename = f"event_logs_{start_date}_{end_date}.csv"
    else:
        raise HTTPException(status_code=400, detail="Invalid report_type. Must be 'summary', 'by_model', 'storage', or 'logs'")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )