from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
import datetime

from .database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String)
    extracted = Column(DateTime, default=datetime.datetime.utcnow)

    chunks = relationship("TextChunk", back_populates="document")
