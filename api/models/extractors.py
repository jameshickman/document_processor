from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Extractor(Base):
    __tablename__ = "extractors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    prompt = Column(Text)

    fields = relationship("ExtractorField", back_populates="extractor")
