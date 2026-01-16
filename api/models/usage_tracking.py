"""
SQLAlchemy models for usage tracking tables
"""

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Date, Text, ForeignKey, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import ARRAY, INET
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

Base = declarative_base()

class UsageLog(Base):
    __tablename__ = 'usage_logs'

    id = Column(BigInteger, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Operation metadata
    operation_type = Column(String(50), nullable=False)  # 'extraction', 'classification', 'embedding', 'upload'
    source_type = Column(String(20), nullable=False)     # 'workbench', 'api'
    
    # Resource identifiers
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=True)
    extractor_id = Column(Integer, ForeignKey('extractors.id'), nullable=True)
    classifier_id = Column(Integer, ForeignKey('classifiers.id'), nullable=True)
    
    # LLM tracking
    llm_model_id = Column(Integer, ForeignKey('llm_models.id'), nullable=True)
    provider = Column(String(50))                        # 'openai', 'deepinfra', 'ollama', 'anthropic'
    model_name = Column(String(255))                     # Actual model used (e.g., 'gpt-4', 'llama-2-70b')
    
    # Token usage (for LLM operations)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    
    # Storage tracking (for upload operations)
    bytes_stored = Column(BigInteger)                    # Size of uploaded/processed file
    
    # Performance metrics
    duration_ms = Column(Integer)                        # Operation duration in milliseconds
    status = Column(String(20))                          # 'success', 'failure', 'partial'
    error_message = Column(Text)                         # If status != 'success'
    
    # Request metadata
    user_agent = Column(Text)
    ip_address = Column(INET)
    
    # Relationships
    account = relationship("Account", back_populates="usage_logs")
    document = relationship("Document", back_populates="usage_logs")
    extractor = relationship("Extractor", back_populates="usage_logs")
    classifier = relationship("Classifier", back_populates="usage_logs")
    llm_model = relationship("LLMModel", back_populates="usage_logs")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            operation_type.in_(['extraction', 'classification', 'embedding', 'upload', 'download']),
            name='check_operation_type'
        ),
        CheckConstraint(
            source_type.in_(['workbench', 'api']),
            name='check_source_type'
        ),
        CheckConstraint(
            status.in_(['success', 'failure', 'partial']),
            name='check_status'
        ),
        Index('idx_usage_logs_account_timestamp', 'account_id', 'timestamp'),
        Index('idx_usage_logs_operation_type', 'operation_type'),
        Index('idx_usage_logs_timestamp', 'timestamp'),
        Index('idx_usage_logs_provider_model', 'provider', 'model_name'),
        Index('idx_usage_logs_source_type', 'source_type'),
    )


class UsageSummary(Base):
    __tablename__ = 'usage_summaries'

    id = Column(BigInteger, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    
    # Time bucket
    date = Column(Date, nullable=False)
    
    # Usage breakdown by source
    workbench_operations = Column(Integer, default=0)
    api_operations = Column(Integer, default=0)
    total_operations = Column(Integer, default=0)
    
    # Operation counts by type
    extractions = Column(Integer, default=0)
    classifications = Column(Integer, default=0)
    embeddings = Column(Integer, default=0)
    uploads = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    
    # LLM usage totals
    total_input_tokens = Column(BigInteger, default=0)
    total_output_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)
    
    # Success rates
    successful_operations = Column(Integer, default=0)
    failed_operations = Column(Integer, default=0)
    
    # Storage
    bytes_uploaded = Column(BigInteger, default=0)
    bytes_downloaded = Column(BigInteger, default=0)
    
    # Performance
    avg_duration_ms = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="usage_summaries")
    
    # Uniqueness constraint
    __table_args__ = (
        UniqueConstraint('account_id', 'date', name='uq_account_date'),
        Index('idx_usage_summaries_account_date', 'account_id', 'date'),
        Index('idx_usage_summaries_date', 'date'),
    )


class UsageSummaryByModel(Base):
    __tablename__ = 'usage_summaries_by_model'

    id = Column(BigInteger, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    
    # Time bucket
    date = Column(Date, nullable=False)
    
    # LLM identification
    provider = Column(String(50), nullable=False)
    model_name = Column(String(255), nullable=False)
    llm_model_id = Column(Integer, ForeignKey('llm_models.id'), nullable=True)
    
    # Usage counts
    operation_count = Column(Integer, default=0)
    
    # Token tracking
    input_tokens = Column(BigInteger, default=0)
    output_tokens = Column(BigInteger, default=0)
    total_tokens = Column(BigInteger, default=0)
    
    # Performance
    avg_duration_ms = Column(Integer)
    
    # Success rate
    successful_operations = Column(Integer, default=0)
    failed_operations = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="usage_summaries_by_model")
    llm_model = relationship("LLMModel", back_populates="usage_summaries_by_model")
    
    # Uniqueness constraint
    __table_args__ = (
        UniqueConstraint('account_id', 'date', 'provider', 'model_name', name='uq_account_date_provider_model'),
        Index('idx_usage_summaries_by_model_account_date', 'account_id', 'date'),
        Index('idx_usage_summaries_by_model_provider_model', 'provider', 'model_name'),
    )


class StorageUsage(Base):
    __tablename__ = 'storage_usage'

    id = Column(BigInteger, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    
    # Time
    date = Column(Date, nullable=False)
    
    # Storage metrics (in bytes)
    total_bytes = Column(BigInteger, nullable=False, default=0)
    document_count = Column(Integer, nullable=False, default=0)
    
    # Storage backend
    storage_backend = Column(String(20))                 # 'local', 's3'
    
    # Breakdown by file type (optional)
    pdf_bytes = Column(BigInteger, default=0)
    docx_bytes = Column(BigInteger, default=0)
    html_bytes = Column(BigInteger, default=0)
    other_bytes = Column(BigInteger, default=0)
    
    # Metadata
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    account = relationship("Account", back_populates="storage_usage")
    
    # Uniqueness constraint
    __table_args__ = (
        UniqueConstraint('account_id', 'date', name='uq_storage_account_date'),
        Index('idx_storage_usage_account_date', 'account_id', 'date'),
        Index('idx_storage_usage_date', 'date'),
    )