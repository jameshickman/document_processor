"""
Background scheduler for usage tracking jobs
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
from sqlalchemy.orm import sessionmaker
from api.models.database import engine
from api.jobs.usage_aggregation import aggregate_yesterday_usage
from api.jobs.storage_calculation import calculate_storage_usage


def create_scheduler():
    """
    Create and configure the background scheduler
    """
    scheduler = AsyncIOScheduler()
    return scheduler


def setup_usage_tracking_jobs(scheduler: AsyncIOScheduler, db_session_factory: sessionmaker):
    """
    Set up all usage tracking background jobs
    
    Args:
        scheduler: The APScheduler instance
        db_session_factory: A factory function that creates database sessions
    """
    # Daily aggregation job - runs at 2 AM every day
    # This aggregates yesterday's usage logs into daily summaries
    scheduler.add_job(
        func=lambda: asyncio.create_task(run_aggregate_job(db_session_factory)),
        trigger=CronTrigger(hour=2, minute=0),  # Run at 2:00 AM daily
        id='daily_usage_aggregation',
        name='Aggregate daily usage statistics',
        replace_existing=True
    )
    
    # Daily storage calculation job - runs at 3 AM every day
    # This calculates storage usage per account
    scheduler.add_job(
        func=lambda: asyncio.create_task(run_storage_calculation_job(db_session_factory)),
        trigger=CronTrigger(hour=3, minute=0),  # Run at 3:00 AM daily
        id='daily_storage_calculation',
        name='Calculate daily storage usage',
        replace_existing=True
    )
    
    print("Usage tracking jobs scheduled:")
    print("- Daily usage aggregation: 2:00 AM")
    print("- Daily storage calculation: 3:00 AM")


async def run_aggregate_job(db_session_factory):
    """
    Wrapper function to run the aggregation job with a fresh database session
    """
    db = db_session_factory()
    try:
        await aggregate_yesterday_usage(db)
        db.commit()
    except Exception as e:
        print(f"Error in daily aggregation job: {e}")
        db.rollback()
    finally:
        db.close()


async def run_storage_calculation_job(db_session_factory):
    """
    Wrapper function to run the storage calculation job with a fresh database session
    """
    db = db_session_factory()
    try:
        await calculate_storage_usage(db)
        db.commit()
    except Exception as e:
        print(f"Error in daily storage calculation job: {e}")
        db.rollback()
    finally:
        db.close()


# For manual triggering of jobs
async def run_manual_aggregation(db_session_factory, target_date):
    """
    Manually run aggregation for a specific date
    """
    db = db_session_factory()
    try:
        from api.jobs.usage_aggregation import aggregate_specific_date_usage
        await aggregate_specific_date_usage(db, target_date)
        db.commit()
    except Exception as e:
        print(f"Error in manual aggregation job: {e}")
        db.rollback()
    finally:
        db.close()


async def run_manual_storage_calculation(db_session_factory, target_date):
    """
    Manually run storage calculation for a specific date
    """
    db = db_session_factory()
    try:
        from api.jobs.storage_calculation import calculate_specific_date_storage
        await calculate_specific_date_storage(db, target_date)
        db.commit()
    except Exception as e:
        print(f"Error in manual storage calculation job: {e}")
        db.rollback()
    finally:
        db.close()