from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from .database import Base

"""
Table: action_chains

Store macros to run against a Document Classification

Fields:
  - ID
  - ClassifierID, foreign key to classifiers
  - Criteria, store a JSON document containing the activation criteria
  - Threshold, Classifier threshold to trigger the action_chains
"""

class ActionChains(Base):
    pass
