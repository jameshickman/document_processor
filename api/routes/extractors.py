from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api import models
from api.models.database import get_db
from pydantic import BaseModel
from typing import List
from lib.fact_extractor.fact_extractor import FactExtractor
from lib.fact_extractor.models import ExtractionQuery
from api.util.llm_config import llm_config
from api.dependencies import get_current_user_info

router = APIRouter()

class ExtractorField(BaseModel):
    name: str
    description: str

class Extractor(BaseModel):
    name: str
    prompt: str
    fields: List[ExtractorField]

@router.post("/{extractor_id}")
def create_or_update_extractor(
        extractor_id: int,
        extractor: Extractor,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    If the extractor_id is 0, create a new record else update.
    """
    if extractor_id == 0:
        # Create new extractor
        db_extractor = models.Extractor(name=extractor.name, prompt=extractor.prompt, account_id=user.user_id)
        db.add(db_extractor)
        db.commit()
        db.refresh(db_extractor)
    else:
        # Update existing extractor
        db_extractor = db.query(models.Extractor).filter(
            and_(
                models.Extractor.account_id == user.user_id,
                models.Extractor.id == extractor_id
            )
        ).first()
        if db_extractor is None:
            raise HTTPException(status_code=404, detail="Extractor not found")
        db_extractor.name = extractor.name
        db_extractor.prompt = extractor.prompt
        # Delete existing fields
        db.query(models.ExtractorField).filter(models.ExtractorField.extractor_id == extractor_id).delete()
        db.commit()
    
    # Add new fields
    for field in extractor.fields:
        db_field = models.ExtractorField(**field.model_dump(), extractor_id=db_extractor.id)
        db.add(db_field)
    db.commit()
    return {"id": db_extractor.id}

@router.get("/")
def list_extractors(
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Return the IDs and names of all the extractors.
    """
    extractors = db.query(models.Extractor).filter(models.Extractor.account_id == user.user_id).all()
    return [{"id": e.id, "name": e.name} for e in extractors]

@router.get("/{extractor_id}")
def get_extractor(
        extractor_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    db_extractor = db.query(models.Extractor).filter(
        and_(
            models.Extractor.account_id == user.user_id,
            models.Extractor.id == extractor_id
        )
    ).first()
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")
    return {
        "name": db_extractor.name,
        "id": db_extractor.id,
        "prompt": db_extractor.prompt,
        "fields": [{"name": field.name, "description": field.description} for field in db_extractor.fields]
    }

@router.get("/run/{extractor_id}/{document_id}")
def run_extractor(
        extractor_id: int,
        document_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Run an extractor against the contents of a document.
    """
    db_extractor = db.query(models.Extractor).filter(
        and_(
            models.Extractor.account_id == user.user_id,
            models.Extractor.id == extractor_id
        )
    ).first()
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")

    document = db.query(models.Document).filter(
        and_(
            models.Document.account_id == user.user_id,
            models.Document.id == document_id
        )
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found or has no content")

    document_text = document.full_text

    fact_extractor = FactExtractor(llm_config)

    extraction_query = ExtractionQuery(
        query=db_extractor.prompt,
        fields={field.name: field.description for field in db_extractor.fields},
    )

    result = fact_extractor.extract_facts(document_text, extraction_query)
    return {"id": extractor_id, "document_id": document_id, "result": result}
