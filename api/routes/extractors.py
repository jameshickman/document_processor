from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models
from ..models import get_db
from pydantic import BaseModel
from typing import List

router = APIRouter()

class ExtractorField(BaseModel):
    name: str
    description: str

class Extractor(BaseModel):
    name: str
    prompt: str
    fields: List[ExtractorField]

@router.post("/")
def create_extractor(extractor: Extractor, db: Session = Depends(get_db)):
    db_extractor = models.Extractor(name=extractor.name, prompt=extractor.prompt)
    db.add(db_extractor)
    db.commit()
    db.refresh(db_extractor)
    for field in extractor.fields:
        db_field = models.ExtractorField(**field.dict(), extractor_id=db_extractor.id)
        db.add(db_field)
    db.commit()
    return db_extractor

@router.get("/{extractor_id}")
def get_extractor(extractor_id: int, db: Session = Depends(get_re_db)):
    db_extractor = db.query(models.Extractor).filter(models.Extractor.id == extractor_id).first()
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")
    return db_extractor
