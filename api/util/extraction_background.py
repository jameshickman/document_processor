"""
Background-process to run an extractor and call a web-hook on completion
"""
from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from pydantic import BaseModel

import api.models as models
from api.util.llm_config import llm_config
from lib.fact_extractor.fact_extractor import FactExtractor

import requests
import logging

from lib.fact_extractor.models import ExtractionQuery


class ExtractionPayload(BaseModel):
    result: dict
    file_name: str
    document_id: int
    csf_token: str


def run_extractor(
        account_id: int,
        extractor_id: int,
        document_id: int,
        db: Session,
        web_hook: str,
        csf_token: str = ''
):
    db_extractor = db.query(models.Extractor).filter(
        and_(
            models.Extractor.account_id == account_id,
            models.Extractor.id == extractor_id
        )
    ).first()
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")

    document = db.query(models.Document).filter(
        and_(
            models.Document.account_id == account_id,
            models.Document.id == document_id
        )
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found or has no content")

    document_text = str(document.full_text)
    file_name = document.file_name.split('/')[-1]

    fact_extractor = FactExtractor(llm_config)

    extraction_query = ExtractionQuery(
        query=db_extractor.prompt,
        fields={field.name: field.description for field in db_extractor.fields},
    )

    result = fact_extractor.extract_facts(document_text, extraction_query)

    payload = ExtractionPayload(
        result=result.model_dump(),
        file_name=file_name,
        document_id=document_id,
        csf_token=csf_token
    ).model_dump()

    r = requests.post(web_hook, json=payload)
    logging.info(f"Extraction Web-hook response: {r}")

    return