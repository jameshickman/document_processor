"""
Background-process to run an extractor and call a web-hook on completion
"""
from sqlalchemy.orm import Session

import api.models
from lib.fact_extractor.fact_extractor import FactExtractor
import requests

def run_extractor(user_id, document_id: int, db: Session):
    return