"""
Self-service usage API endpoints for authenticated users
All users can view their own usage data, graphs, and download CSV reports
Uses POST for all endpoints to work seamlessly with API.js
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from pydantic import BaseModel, Field
from api.models.database import get_db
from api.rbac import get_current_user
from api.services.usage_service import UsageService
from api.util.csv_export import (
    export_usage_summary_csv,
    export_model_usage_csv,
    export_storage_usage_csv
)

router = APIRouter()


# Request models for POST endpoints
class UsageSummaryRequest(BaseModel):
    start_date: str = Field(..., description="Start date (ISO format: YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (ISO format: YYYY-MM-DD)")
    group_by: str = Field(default="day", description="Grouping: day, week, month")


class ModelUsageRequest(BaseModel):
    start_date: str = Field(..., description="Start date (ISO format: YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (ISO format: YYYY-MM-DD)")
    provider: Optional[str] = Field(default=None, description="Filter by provider")
    model_name: Optional[str] = Field(default=None, description="Filter by model name")


class StorageUsageRequest(BaseModel):
    start_date: str = Field(..., description="Start date (ISO format: YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (ISO format: YYYY-MM-DD)")


class ExportRequest(BaseModel):
    start_date: str = Field(..., description="Start date (ISO format: YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (ISO format: YYYY-MM-DD)")
    report_type: str = Field(..., description="Report type: summary, by_model, storage")


@router.post("/my-summary")
async def get_my_usage_summary(
    request: UsageSummaryRequest,
    user_info: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage summary for the authenticated user's account.

    Returns usage statistics including operations, tokens, and success rates.
    """
    try:
        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

    account_id = user_info.get("user_id")
    if not account_id:
        return {"error": "User ID not found in token"}

    service = UsageService(db)
    return service.get_my_summary(account_id, start_date, end_date, request.group_by)


@router.post("/my-models")
async def get_my_model_usage(
    request: ModelUsageRequest,
    user_info: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get model usage breakdown for the authenticated user's account.

    Shows token usage by LLM provider and model.
    """
    try:
        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

    account_id = user_info.get("user_id")
    if not account_id:
        return {"error": "User ID not found in token"}

    service = UsageService(db)
    return service.get_my_models(
        account_id,
        start_date,
        end_date,
        request.provider,
        request.model_name
    )


@router.post("/my-storage")
async def get_my_storage_usage(
    request: StorageUsageRequest,
    user_info: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get storage usage for the authenticated user's account.

    Shows document storage consumption over time.
    """
    try:
        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

    account_id = user_info.get("user_id")
    if not account_id:
        return {"error": "User ID not found in token"}

    service = UsageService(db)
    return service.get_my_storage(account_id, start_date, end_date)


@router.post("/my-export/csv")
async def export_my_usage_csv(
    request: ExportRequest,
    user_info: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export usage data to CSV for the authenticated user's account.

    Returns a CSV file download.
    """
    try:
        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

    account_id = user_info.get("user_id")
    if not account_id:
        return {"error": "User ID not found in token"}

    # Generate CSV based on report type
    if request.report_type == "summary":
        csv_content = export_usage_summary_csv(db, start_date, end_date, account_id)
        filename = f"my_usage_summary_{start_date}_{end_date}.csv"
    elif request.report_type == "by_model":
        csv_content = export_model_usage_csv(db, start_date, end_date, account_id)
        filename = f"my_usage_by_model_{start_date}_{end_date}.csv"
    elif request.report_type == "storage":
        csv_content = export_storage_usage_csv(db, start_date, end_date, account_id)
        filename = f"my_storage_usage_{start_date}_{end_date}.csv"
    else:
        return {"error": f"Invalid report type: {request.report_type}"}

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
