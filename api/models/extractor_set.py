from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class ExtractorSet(Base):
    __tablename__ = "extractor_sets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    doc_types = relationship("Classifier", back_populates="extractor")