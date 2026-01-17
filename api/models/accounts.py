from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, func
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
    # New fields for usage tracking and admin access
    is_admin = Column(Boolean, default=False)  # Admin flag for legacy support
    roles = Column(ARRAY(String), default=[])
    usage_tracking_enabled = Column(Boolean, default=True)
    usage_limit_tokens = Column(Integer)  # Optional token limit per month
    usage_alert_threshold = Column(Float)  # Alert at % of limit (e.g., 0.8 = 80%)

    documents = relationship("Document", back_populates="account")
    classifier_sets = relationship("ClassifierSet", back_populates="account")
    extractors = relationship("Extractor", back_populates="account")
    llm_models = relationship("LLMModel", back_populates="account")
