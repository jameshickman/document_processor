"""
Storage calculation jobs for tracking storage usage per account
"""

import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from api.models import Document, StorageUsage
from api.services.usage_tracker import UsageTracker
from api.util.files_abstraction import get_filesystem


async def calculate_storage_usage(db_session: Session):
    """
    Calculate storage usage for all accounts for today.
    This should be run as a daily scheduled job.
    """
    today = date.today()
    
    tracker = UsageTracker(db_session)
    await tracker.calculate_storage_usage(today)
    
    print(f"Completed storage calculation for {today}")


async def calculate_specific_date_storage(db_session: Session, target_date: date):
    """
    Calculate storage usage for all accounts for a specific date.
    Useful for backfilling or re-processing.
    """
    tracker = UsageTracker(db_session)
    await tracker.calculate_storage_usage(target_date)
    
    print(f"Completed storage calculation for {target_date}")


def get_account_storage_usage(account_id: int, db_session: Session) -> dict:
    """
    Calculate current storage usage for a specific account.
    
    Args:
        account_id: The account ID to calculate storage for
        db_session: Database session
        
    Returns:
        Dictionary with storage usage information
    """
    fs = get_filesystem()
    
    # Get all documents for the account
    documents = db_session.query(Document).filter(
        Document.account_id == account_id
    ).all()
    
    total_bytes = 0
    document_count = 0
    pdf_bytes = 0
    docx_bytes = 0
    html_bytes = 0
    other_bytes = 0
    
    for document in documents:
        # Get file size from storage
        try:
            file_size = fs.get_file_size(document.file_name)
            if file_size:
                total_bytes += file_size
                document_count += 1
                
                # Categorize by file extension
                filename_lower = document.file_name.lower()
                if filename_lower.endswith('.pdf'):
                    pdf_bytes += file_size
                elif filename_lower.endswith('.docx'):
                    docx_bytes += file_size
                elif filename_lower.endswith('.html') or filename_lower.endswith('.htm'):
                    html_bytes += file_size
                else:
                    other_bytes += file_size
        except Exception:
            # If we can't get the file size, skip this document
            continue
    
    return {
        'account_id': account_id,
        'total_bytes': total_bytes,
        'document_count': document_count,
        'storage_backend': fs.__class__.__name__.lower().replace('filesystem', ''),
        'pdf_bytes': pdf_bytes,
        'docx_bytes': docx_bytes,
        'html_bytes': html_bytes,
        'other_bytes': other_bytes,
        'calculated_at': datetime.now()
    }