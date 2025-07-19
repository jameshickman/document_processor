from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api import models
from api.models.database import get_db
from pydantic import BaseModel
from typing import List
from lib.classifier import document_classifier_simple

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

@router.get("/run/{classifier_id}/{document_id}")
def run_classifier(classifier_id: int, document_id: int, db: Session = Depends(get_db)):
    db_classifier = db.query(models.Classifier).filter(models.Classifier.id == classifier_id).first()
    if db_classifier is None:
        raise HTTPException(status_code=404, detail="Classifier not found")

    db_chunks = db.query(models.TextChunk).filter(models.TextChunk.document_id == document_id).all()
    if not db_chunks:
        raise HTTPException(status_code=404, detail="Document not found or has no content")

    document_text = " ".join([chunk.chunk for chunk in db_chunks])

    classifications_data = [
        {
            "name": db_classifier.name,
            "terms": [
                {"term": t.term, "distance": t.distance, "weight": t.weight}
                for t in db_classifier.terms
            ],
        }
    ]

    results = document_classifier_simple(document_text, classifications_data)
    return results
