from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class Classifier(Base):
    __tablename__ = "classifiers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    classifier_set = Column(Integer, ForeignKey("classifier_sets.id"))

    terms = relationship("ClassifierTerm", back_populates="classifier")
    classifier_sets = relationship("ClassifierSet", back_populates="classifiers")
