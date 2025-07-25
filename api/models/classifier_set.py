from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base

class ClassifierSet(Base):
    __tablename__ = "classifier_sets"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    account_id = Column(Integer, ForeignKey("accounts.id"))

    classifiers = relationship("Classifier", back_populates="classifier_sets", cascade="all, delete-orphan")
    account = relationship("Account", back_populates="documents")
