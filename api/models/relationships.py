"""
Configure relationships between models after they are all loaded to avoid circular import issues.
"""

from sqlalchemy.orm import relationship
from .accounts import Account
from .usage_tracking import UsageLog, UsageSummary, UsageSummaryByModel, StorageUsage


def configure_relationships():
    """
    Configure relationships after all models are loaded.
    This avoids circular import issues.
    """
    # Establish relationships for Account model
    Account.usage_logs = relationship("UsageLog", back_populates="account")
    Account.usage_summaries = relationship("UsageSummary", back_populates="account") 
    Account.usage_summaries_by_model = relationship("UsageSummaryByModel", back_populates="account")
    Account.storage_usage = relationship("StorageUsage", back_populates="account")
    
    # Establish reverse relationships for usage tracking models
    UsageLog.account = relationship("Account", back_populates="usage_logs")
    UsageSummary.account = relationship("Account", back_populates="usage_summaries")
    UsageSummaryByModel.account = relationship("Account", back_populates="usage_summaries_by_model")
    StorageUsage.account = relationship("Account", back_populates="storage_usage")