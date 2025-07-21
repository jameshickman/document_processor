from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api import models
from api.models.database import get_db
from pydantic import BaseModel
from typing import List
from lib.fact_extractor.fact_extractor import FactExtractor
from lib.fact_extractor.models import LLMConfig, ExtractionQuery
import os

router = APIRouter()

class ExtractorField(BaseModel):
    name: str
    description: str

class Extractor(BaseModel):
    name: str
    prompt: str
    fields: List[ExtractorField]

class ExtractorSet(BaseModel):
    name: str
    doc_types: List[Extractor]

@router.post("/{extractor_id}")
def create_or_update_extractor(extractor_id: int, extractor: ExtractorSet, db: Session = Depends(get_db)):
    """
    If the extractor_id is 0, create a new record else update.
    """
    if extractor_id == 0:
        # Create new extractor
        db_extractor = models.Extractor(name=extractor.name, prompt=extractor.prompt)
        db.add(db_extractor)
        db.commit()
        db.refresh(db_extractor)
    else:
        # Update existing extractor
        db_extractor = db.query(models.Extractor).filter(models.Extractor.id == extractor_id).first()
        if db_extractor is None:
            raise HTTPException(status_code=404, detail="Extractor not found")
        db_extractor.name = extractor.name
        db_extractor.prompt = extractor.prompt
        # Delete existing fields
        db.query(models.ExtractorField).filter(models.ExtractorField.extractor_id == extractor_id).delete()
        db.commit()
    
    # Add new fields
    for field in extractor.fields:
        db_field = models.ExtractorField(**field.dict(), extractor_id=db_extractor.id)
        db.add(db_field)
    db.commit()
    return db_extractor

@router.get("/")
def list_extractors(db: Session = Depends(get_db)):
    """
    Return the IDs and names of all the extractors.
    """
    extractors = db.query(models.Extractor).all()
    return [{"id": e.id, "name": e.name} for e in extractors]

@router.get("/{extractor_id}")
def get_extractor(extractor_id: int, db: Session = Depends(get_db)):
    db_extractor = db.query(models.Extractor).filter(models.Extractor.id == extractor_id).first()
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")
    return db_extractor

@router.get("/run/{extractor_id}/{document_id}")
def run_extractor(extractor_id: int, document_id: int, db: Session = Depends(get_db)):
    """
    Run an extractor against the contents of a document.
    """
    db_extractor = db.query(models.Extractor).filter(models.Extractor.id == extractor_id).first()
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")

    db_chunks = db.query(models.TextChunk).filter(models.TextChunk.document_id == document_id).all()
    if not db_chunks:
        raise HTTPException(status_code=404, detail="Document not found or has no content")

    document_text = " ".join([chunk.chunk for chunk in db_chunks])

    llm_config = LLMConfig(
        base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.environ.get("OPENAI_API_KEY", "openai_api_key"),
        model_name=os.environ.get("OPENAI_MODEL_NAME", "gemma3n"), # gpt-4
        temperature=float(os.environ.get("OPENAI_TEMPERATURE", 0.0)),
        max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", 2048)),
        timeout=int(os.environ.get("OPENAI_TIMEOUT", 120)),
    )

    fact_extractor = FactExtractor(llm_config)

    extraction_query = ExtractionQuery(
        query=db_extractor.prompt,
        fields={field.name: field.description for field in db_extractor.fields},
    )

    result = fact_extractor.extract_facts(document_text, extraction_query)
    return result
