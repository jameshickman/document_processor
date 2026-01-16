"""
Background-process to run an extractor and call a web-hook on completion
"""
import time
from fastapi import HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session

from pydantic import BaseModel

import api.models as models
from api.util.llm_config import llm_config
from api.util.extraction_core import run_extractor_with_markup
from api.services.usage_tracker import UsageTracker

import requests
import logging


class ExtractionPayload(BaseModel):
    result: dict
    file_name: str
    document_id: int
    csrf_token: str


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

    # Run extractor with markup using shared utility
    execution_result = run_extractor_with_markup(
        document_text=document_text,
        document_file_path=document.file_name,
        extractor_prompt=str(db_extractor.prompt),
        extractor_fields={field.name: field.description for field in db_extractor.fields},
        extractor_id=extractor_id,
        llm_config=llm_config,
        use_logging=True,  # Use logging module in background processes
        db=db,
        document_id=document_id,
        use_vector_search=True,
        llm_model_id=db_extractor.llm_model_id,
        account_id=account_id,
        source_type='api'  # Background processes are considered API usage
    )

    payload = ExtractionPayload(
        result=execution_result.extraction_result.model_dump(),
        file_name=file_name,
        document_id=document_id,
        csrf_token=csf_token
    ).model_dump()

    # Add marked PDF information to the payload
    payload['marked_pdf_available'] = execution_result.marked_pdf_available
    if execution_result.marked_pdf_path:
        payload['marked_pdf_path'] = execution_result.marked_pdf_path

    try:
        r = requests.post(web_hook, json=payload)
        logging.info(f"Extraction Web-hook response: {r}")
    except Exception as e:
        logging.error(f"Error calling extraction web-hook: {e}")

    return