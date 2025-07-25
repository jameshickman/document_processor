from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class Extractor(Base):
    __tablename__ = "extractors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    prompt = Column(Text)
    account_id = Column(Integer, ForeignKey("accounts.id"))

    fields = relationship("ExtractorField", back_populates="extractor")
    account = relationship("Account", back_populates="extractors")
