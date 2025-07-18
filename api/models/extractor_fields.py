from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class ExtractorField(Base):
    __tablename__ = "extractor_fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    extractor_id = Column(Integer, ForeignKey("extractors.id"))

    extractor = relationship("Extractor", back_populates="fields")
