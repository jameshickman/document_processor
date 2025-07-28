from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship

from .database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    active = Column(Boolean, default=True)
    grandfathered = Column(Boolean, default=False)
    api_key = Column(String, unique=True, default=None)
    api_secret = Column(String)
    password_local = Column(String, default=None)
    password_encrypted = Column(Boolean, default=False)
    password_salt = Column(String, default=None)

    documents = relationship("Document", back_populates="account")
    classifier_sets = relationship("ClassifierSet", back_populates="account")
    extractors = relationship("Extractor", back_populates="account")