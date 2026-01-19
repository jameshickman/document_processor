from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, case
from typing import List, Optional
from datetime import datetime, date
from api.models.database import get_db
from api.rbac import require_reporting_role
from api.models import UsageSummary, UsageSummaryByModel, StorageUsage, Account, UsageLog
from pydantic import BaseModel, Field
from api.util.csv_export import (
    export_usage_summary_csv,
    export_model_usage_csv,
    export_storage_usage_csv,
    export_event_logs_csv
)

router = APIRouter()


# Helper functions for on-the-fly aggregation
def aggregate_usage_summary_from_logs(db: Session, start_date: date, end_date: date, account_id: Optional[int] = None):
    """
    Aggregate usage summary from usage_logs table on-the-fly.
    Returns a list of dictionary objects that mimic UsageSummary objects.
    """
    from sqlalchemy import cast, Date

    query = db.query(
        cast(UsageLog.timestamp, Date).label('date'),
        UsageLog.account_id,
        Account.name.label('account_name'),
        func.sum(case((UsageLog.source_type == 'workbench', 1), else_=0)).label('workbench_operations'),
        func.sum(case((UsageLog.source_type == 'api', 1), else_=0)).label('api_operations'),
        func.count(UsageLog.id).label('total_operations'),
        func.sum(case((UsageLog.operation_type == 'extraction', 1), else_=0)).label('extractions'),
        func.sum(case((UsageLog.operation_type == 'classification', 1), else_=0)).label('classifications'),
        func.sum(case((UsageLog.operation_type == 'embedding', 1), else_=0)).label('embeddings'),
        func.sum(case((UsageLog.operation_type == 'upload', 1), else_=0)).label('uploads'),
        func.sum(UsageLog.input_tokens).label('total_input_tokens'),
        func.sum(UsageLog.output_tokens).label('total_output_tokens'),
        func.sum(UsageLog.total_tokens).label('total_tokens'),
        func.sum(case((UsageLog.status == 'success', 1), else_=0)).label('successful_operations'),
        func.sum(case((UsageLog.status == 'failure', 1), else_=0)).label('failed_operations'),
    ).join(Account, UsageLog.account_id == Account.id).filter(
        and_(
            cast(UsageLog.timestamp, Date) >= start_date,
            cast(UsageLog.timestamp, Date) <= end_date
        )
    )

    if account_id:
        query = query.filter(UsageLog.account_id == account_id)

    query = query.group_by(cast(UsageLog.timestamp, Date), UsageLog.account_id, Account.name)
    query = query.order_by(cast(UsageLog.timestamp, Date))

    results = query.all()

    # Convert to objects that look like UsageSummary
    class SummaryProxy:
        def __init__(self, row):
            self.date = row.date
            self.account_id = row.account_id
            self.account = type('obj', (object,), {'name': row.account_name})()
            self.workbench_operations = row.workbench_operations or 0
            self.api_operations = row.api_operations or 0
            self.total_operations = row.total_operations or 0
            self.extractions = row.extractions or 0
            self.classifications = row.classifications or 0
            self.embeddings = row.embeddings or 0
            self.uploads = row.uploads or 0
            self.total_input_tokens = row.total_input_tokens or 0
            self.total_output_tokens = row.total_output_tokens or 0
            self.total_tokens = row.total_tokens or 0
            self.successful_operations = row.successful_operations or 0
            self.failed_operations = row.failed_operations or 0

    return [SummaryProxy(row) for row in results]


def aggregate_model_usage_from_logs(db: Session, start_date: date, end_date: date, account_id: Optional[int] = None, provider: Optional[str] = None, model_name: Optional[str] = None):
    """
    Aggregate model usage from usage_logs table on-the-fly.
    """
    from sqlalchemy import cast, Date

    query = db.query(
        cast(UsageLog.timestamp, Date).label('date'),
        UsageLog.account_id,
        Account.name.label('account_name'),
        UsageLog.provider,
        UsageLog.model_name,
        func.count(UsageLog.id).label('operation_count'),
        func.sum(UsageLog.input_tokens).label('input_tokens'),
        func.sum(UsageLog.output_tokens).label('output_tokens'),
        func.sum(UsageLog.total_tokens).label('total_tokens'),
        func.avg(UsageLog.duration_ms).label('avg_duration_ms'),
        func.sum(case((UsageLog.status == 'success', 1), else_=0)).label('successful_operations'),
        func.sum(case((UsageLog.status == 'failure', 1), else_=0)).label('failed_operations'),
    ).join(Account, UsageLog.account_id == Account.id).filter(
        and_(
            cast(UsageLog.timestamp, Date) >= start_date,
            cast(UsageLog.timestamp, Date) <= end_date,
            UsageLog.provider.isnot(None)
        )
    )

    if account_id:
        query = query.filter(UsageLog.account_id == account_id)
    if provider:
        query = query.filter(UsageLog.provider == provider)
    if model_name:
        query = query.filter(UsageLog.model_name == model_name)

    query = query.group_by(
        cast(UsageLog.timestamp, Date),
        UsageLog.account_id,
        Account.name,
        UsageLog.provider,
        UsageLog.model_name
    )
    query = query.order_by(cast(UsageLog.timestamp, Date))

    results = query.all()

    # Convert to objects that look like UsageSummaryByModel
    class ModelSummaryProxy:
        def __init__(self, row):
            self.date = row.date
            self.account_id = row.account_id
            self.account = type('obj', (object,), {'name': row.account_name})()
            self.provider = row.provider
            self.model_name = row.model_name
            self.operation_count = row.operation_count or 0
            self.input_tokens = row.input_tokens or 0
            self.output_tokens = row.output_tokens or 0
            self.total_tokens = row.total_tokens or 0
            self.avg_duration_ms = int(row.avg_duration_ms) if row.avg_duration_ms else None
            self.successful_operations = row.successful_operations or 0
            self.failed_operations = row.failed_operations or 0

    return [ModelSummaryProxy(row) for row in results]


# Request models for POST endpoints
class UsageReportRequest(BaseModel):
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    account_id: Optional[int] = Field(None, description="Filter by specific account ID")
    group_by: str = Field("day", description="Group by 'day', 'week', or 'month'")


class ModelUsageRequest(BaseModel):
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    account_id: Optional[int] = Field(None, description="Filter by specific account ID")
    provider: Optional[str] = Field(None, description="Filter by provider")
    model_name: Optional[str] = Field(None, description="Filter by model name")


class StorageUsageRequest(BaseModel):
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    account_id: Optional[int] = Field(None, description="Filter by specific account ID")


class EventLogsRequest(BaseModel):
    start_date: str = Field(..., description="Start date and time (YYYY-MM-DDTHH:MM:SS)")
    end_date: str = Field(..., description="End date and time (YYYY-MM-DDTHH:MM:SS)")
    account_id: Optional[int] = Field(None, description="Filter by specific account ID")
    operation_type: Optional[str] = Field(None, description="Filter by operation type")
    source_type: Optional[str] = Field(None, description="Filter by source type")
    status: Optional[str] = Field(None, description="Filter by status")
    limit: int = Field(100, ge=1, le=1000, description="Number of records to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")


# Response models
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


@router.post("/usage/summary", response_model=UsageSummaryResponse)
def get_usage_summary(
    request: UsageReportRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_reporting_role)
):
    """
    Get usage summary aggregated by date range.
    If summary tables are empty, aggregate from usage_logs on-the-fly.
    """
    # Parse dates from strings
    start_date = date.fromisoformat(request.start_date)
    end_date = date.fromisoformat(request.end_date)

    query = db.query(UsageSummary).filter(
        and_(
            UsageSummary.date >= start_date,
            UsageSummary.date <= end_date
        )
    )

    if request.account_id:
        query = query.filter(UsageSummary.account_id == request.account_id)

    # Join with accounts to get account names
    query = query.join(Account, UsageSummary.account_id == Account.id)

    summaries = query.all()

    # If no summaries found, aggregate from usage_logs on-the-fly
    if not summaries:
        summaries = aggregate_usage_summary_from_logs(db, start_date, end_date, request.account_id)

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
        start_date=request.start_date,
        end_date=request.end_date,
        group_by=request.group_by,
        data=data,
        total_records=len(data)
    )


@router.post("/usage/by-model", response_model=ModelUsageResponse)
def get_model_usage(
    request: ModelUsageRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_reporting_role)
):
    """
    Get usage breakdown by model.
    If summary tables are empty, aggregate from usage_logs on-the-fly.
    """
    # Parse dates from strings
    start_date = date.fromisoformat(request.start_date)
    end_date = date.fromisoformat(request.end_date)

    query = db.query(UsageSummaryByModel).filter(
        and_(
            UsageSummaryByModel.date >= start_date,
            UsageSummaryByModel.date <= end_date
        )
    )

    if request.account_id:
        query = query.filter(UsageSummaryByModel.account_id == request.account_id)
    if request.provider:
        query = query.filter(UsageSummaryByModel.provider == request.provider)
    if request.model_name:
        query = query.filter(UsageSummaryByModel.model_name == request.model_name)

    # Join with accounts to get account names
    query = query.join(Account, UsageSummaryByModel.account_id == Account.id)

    summaries = query.all()

    # If no summaries found, aggregate from usage_logs on-the-fly
    if not summaries:
        summaries = aggregate_model_usage_from_logs(db, start_date, end_date, request.account_id, request.provider, request.model_name)

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
        start_date=request.start_date,
        end_date=request.end_date,
        data=data
    )


@router.post("/storage", response_model=StorageUsageResponse)
def get_storage_usage(
    request: StorageUsageRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_reporting_role)
):
    """
    Get storage usage by date range.
    """
    # Parse dates from strings
    start_date = date.fromisoformat(request.start_date)
    end_date = date.fromisoformat(request.end_date)

    query = db.query(StorageUsage).filter(
        and_(
            StorageUsage.date >= start_date,
            StorageUsage.date <= end_date
        )
    )

    if request.account_id:
        query = query.filter(StorageUsage.account_id == request.account_id)

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
        start_date=request.start_date,
        end_date=request.end_date,
        data=data
    )


@router.post("/logs", response_model=EventLogsResponse)
def get_event_logs(
    request: EventLogsRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_reporting_role)
):
    """
    Get raw usage event logs.
    """
    # Parse datetime strings
    start_date = datetime.fromisoformat(request.start_date)
    end_date = datetime.fromisoformat(request.end_date)

    query = db.query(UsageLog).filter(
        and_(
            UsageLog.timestamp >= start_date,
            UsageLog.timestamp <= end_date
        )
    )

    if request.account_id:
        query = query.filter(UsageLog.account_id == request.account_id)
    if request.operation_type:
        query = query.filter(UsageLog.operation_type == request.operation_type)
    if request.source_type:
        query = query.filter(UsageLog.source_type == request.source_type)
    if request.status:
        query = query.filter(UsageLog.status == request.status)

    # Join with accounts to get account names
    query = query.join(Account, UsageLog.account_id == Account.id)

    # Apply pagination
    logs = query.order_by(UsageLog.timestamp.desc()).offset(request.offset).limit(request.limit).all()

    # Count total records for pagination info
    total_query = db.query(func.count(UsageLog.id)).filter(
        and_(
            UsageLog.timestamp >= start_date,
            UsageLog.timestamp <= end_date
        )
    )
    if request.account_id:
        total_query = total_query.filter(UsageLog.account_id == request.account_id)
    if request.operation_type:
        total_query = total_query.filter(UsageLog.operation_type == request.operation_type)
    if request.source_type:
        total_query = total_query.filter(UsageLog.source_type == request.source_type)
    if request.status:
        total_query = total_query.filter(UsageLog.status == request.status)

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
        start_date=request.start_date,
        end_date=request.end_date,
        filters={
            "account_id": request.account_id,
            "operation_type": request.operation_type,
            "source_type": request.source_type,
            "status": request.status
        },
        pagination={
            "limit": request.limit,
            "offset": request.offset,
            "total": total_count
        },
        data=data
    )


@router.get("/accounts", response_model=AccountsResponse)
def get_accounts(
    active_only: bool = Query(True, description="Return only active accounts"),
    db: Session = Depends(get_db),
    _: dict = Depends(require_reporting_role)
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
    _: dict = Depends(require_reporting_role)
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