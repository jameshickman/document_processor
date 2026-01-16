from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship

from .database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    active = Column(Boolean, default=True)
    grandfathered = Column(Boolean, default=False)
    api_key = Column(String, unique=True, default=None)
    api_secret = Column(String)
    password_local = Column(String, default=None)
    password_encrypted = Column(Boolean, default=False)
    password_salt = Column(String, default=None)
    # New fields for usage tracking
    roles = Column(ARRAY(String), default=[])
    usage_tracking_enabled = Column(Boolean, default=True)
    usage_limit_tokens = Column(Integer)  # Optional token limit per month
    usage_alert_threshold = Column(Integer)  # Alert at % of limit (e.g., 80 = 80%)

    documents = relationship("Document", back_populates="account")
    classifier_sets = relationship("ClassifierSet", back_populates="account")
    extractors = relationship("Extractor", back_populates="account")
    llm_models = relationship("LLMModel", back_populates="account")
    # New relationships for usage tracking
    usage_logs = relationship("UsageLog", back_populates="account")
    usage_summaries = relationship("UsageSummary", back_populates="account")
    usage_summaries_by_model = relationship("UsageSummaryByModel", back_populates="account")
    storage_usage = relationship("StorageUsage", back_populates="account")