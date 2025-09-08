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

    fact_extractor = FactExtractor(llm_config)

    extraction_query = ExtractionQuery(
        query=str(db_extractor.prompt),
        fields={field.name: field.description for field in db_extractor.fields},
    )

    result = fact_extractor.extract_facts(document_text, extraction_query)

    # Create marked-up PDF if extraction was successful and citations exist
    marked_pdf_path = None
    marked_pdf_available = False
    
    if result.found and result.extracted_data:
        try:
            from api.to_pdf.converter import to_pdf, ConversionError
            from api.pdf_markup.highlight_pdf import highlight_pdf
            import os
            
            # Collect all citations from all fields
            all_citations = []
            for field_name, field_data in result.extracted_data.items():
                if isinstance(field_data, dict) and 'citation' in field_data:
                    citations = field_data['citation']
                    if isinstance(citations, list):
                        all_citations.extend(citations)
                    elif isinstance(citations, str):
                        all_citations.append(citations)
            
            # Only proceed if we have citations to highlight
            if all_citations:
                # Remove empty citations and duplicates
                all_citations = list(set([c for c in all_citations if c and c.strip()]))
                
                if all_citations:
                    # Determine source PDF path
                    source_pdf_path = document.file_name
                    
                    # If the original file is not a PDF, convert it first
                    if not source_pdf_path.lower().endswith('.pdf'):
                        try:
                            source_pdf_path = to_pdf(document.file_name)
                        except ConversionError as e:
                            logging.warning(f"Could not convert {document.file_name} to PDF: {e}")
                            source_pdf_path = None
                    
                    # Create marked-up PDF with citations highlighted
                    if source_pdf_path and os.path.exists(source_pdf_path):
                        try:
                            marked_pdf_path = highlight_pdf(
                                input_file=source_pdf_path,
                                strings=all_citations,
                                extractor_id=extractor_id
                            )
                            marked_pdf_available = True
                            logging.info(f"Created marked-up PDF: {marked_pdf_path}")
                        except Exception as e:
                            logging.error(f"Could not create marked-up PDF: {e}")
                            marked_pdf_path = None
        
        except Exception as e:
            logging.error(f"Error during PDF markup process: {e}")
            marked_pdf_path = None

    payload = ExtractionPayload(
        result=result.model_dump(),
        file_name=file_name,
        document_id=document_id,
        csrf_token=csf_token
    ).model_dump()
    
    # Add marked PDF information to the payload
    payload['marked_pdf_available'] = marked_pdf_available
    if marked_pdf_path:
        payload['marked_pdf_path'] = marked_pdf_path

    try:
        r = requests.post(web_hook, json=payload)
        logging.info(f"Extraction Web-hook response: {r}")
    except Exception as e:
        logging.error(f"Error calling extraction web-hook: {e}")

    return