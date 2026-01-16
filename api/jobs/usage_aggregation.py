"""
Aggregation jobs for daily rollups of usage data
"""

import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from api.services.usage_tracker import UsageTracker


async def aggregate_yesterday_usage(db_session: Session):
    """
    Aggregate usage from yesterday into daily summaries.
    This should be run as a daily scheduled job.
    """
    # Calculate yesterday's date
    yesterday = date.today() - timedelta(days=1)
    
    tracker = UsageTracker(db_session)
    await tracker.aggregate_daily_usage(yesterday)
    
    print(f"Completed aggregation for {yesterday}")


async def aggregate_specific_date_usage(db_session: Session, target_date: date):
    """
    Aggregate usage for a specific date.
    Useful for backfilling or re-processing.
    """
    tracker = UsageTracker(db_session)
    await tracker.aggregate_daily_usage(target_date)
    
    print(f"Completed aggregation for {target_date}")


async def aggregate_range_usage(db_session: Session, start_date: date, end_date: date):
    """
    Aggregate usage for a range of dates.
    Useful for backfilling historical data.
    """
    current_date = start_date
    while current_date <= end_date:
        tracker = UsageTracker(db_session)
        await tracker.aggregate_daily_usage(current_date)
        print(f"Completed aggregation for {current_date}")
        current_date += timedelta(days=1)