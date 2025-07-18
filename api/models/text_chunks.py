from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class TextChunk(Base):
    __tablename__ = "text_chunks"

    id = Column(Integer, primary_key=True, index=True)
    chunk = Column(Text)
    document_id = Column(Integer, ForeignKey("documents.id"))

    document = relationship("Document", back_populates="chunks")
