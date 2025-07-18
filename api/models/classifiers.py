from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class Classifier(Base):
    __tablename__ = "classifiers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    terms = relationship("ClassifierTerm", back_populates="classifier")
