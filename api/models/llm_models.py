from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class LLMModel(Base):
    __tablename__ = "llm_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)  # User-friendly display name
    provider = Column(String, nullable=False)  # "openai", "deepinfra", "ollama"
    model_identifier = Column(String, nullable=False)  # Actual model name for API
    base_url = Column(String, nullable=True)  # Optional custom base URL
    temperature = Column(Float, default=0.0)
    max_tokens = Column(Integer, default=2048)
    timeout = Column(Integer, default=360)
    model_kwargs_json = Column(Text, nullable=True)  # JSON string for additional params
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    # Relationships
    account = relationship("Account", back_populates="llm_models")
    extractors = relationship("Extractor", back_populates="llm_model")
