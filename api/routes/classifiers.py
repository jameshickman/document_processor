from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models
from ..models import get_db
from pydantic import BaseModel
from typing import List

router = APIRouter()

class ClassifierTerm(BaseModel):
    term: str
    distance: int
    weight: float

class Classifier(BaseModel):
    name: str
    terms: List[ClassifierTerm]

@router.post("/")
def create_classifier(classifier: Classifier, db: Session = Depends(get_db)):
    db_classifier = models.Classifier(name=classifier.name)
    db.add(db_classifier)
    db.commit()
    db.refresh(db_classifier)
    for term in classifier.terms:
        db_term = models.ClassifierTerm(**term.dict(), classifier_id=db_classifier.id)
        db.add(db_term)
    db.commit()
    return db_classifier

@router.get("/{classifier_id}")
def get_classifier(classifier_id: int, db: Session = Depends(get_db)):
    db_classifier = db.query(models.Classifier).filter(models.Classifier.id == classifier_id).first()
    if db_classifier is None:
        raise HTTPException(status_code=404, detail="Classifier not found")
    return db_classifier
