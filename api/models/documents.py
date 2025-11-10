from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime

from .database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String)
    extracted = Column(DateTime, default=datetime.datetime.utcnow)
    full_text = Column(String)
    account_id = Column(Integer, ForeignKey("accounts.id"))

    account = relationship("Account", back_populates="documents")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")

