from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .database import Base

class ClassifierSet(Base):
    __tablename__ = "classifier_sets"
    id = Column(Integer, primary_key=True)
    name = Column(String)

    classifiers = relationship("Classifier", back_populates="classifier_sets", cascade="all, delete-orphan")
