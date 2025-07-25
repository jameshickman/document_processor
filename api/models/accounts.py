from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from .database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    active = Column(Boolean, default=True)
    grandfathered = Column(Boolean, default=False)
    api_key = Column(String, unique=True, default=None)
    api_secret = Column(String)

    documents = relationship("Document", back_populates="account")
    classifiers = relationship("Classifier", back_populates="account")