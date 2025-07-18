from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class ClassifierTerm(Base):
    __tablename__ = "classifier_terms"

    id = Column(Integer, primary_key=True, index=True)
    term = Column(String)
    distance = Column(Integer)
    weight = Column(Float)
    classifier_id = Column(Integer, ForeignKey("classifiers.id"))

    classifier = relationship("Classifier", back_populates="terms")
