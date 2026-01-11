from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class Extractor(Base):
    __tablename__ = "extractors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    prompt = Column(Text)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    llm_model_id = Column(Integer, ForeignKey("llm_models.id"), nullable=True)

    fields = relationship("ExtractorField", back_populates="extractor")
    account = relationship("Account", back_populates="extractors")
    llm_model = relationship("LLMModel", back_populates="extractors")
