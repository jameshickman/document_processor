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

@router.post("/{classifier_id}")
def create_or_update_classifier(classifier_id: int, classifier: Classifier, db: Session = Depends(get_db)):
    """
    If the classifier_id is 0, create a new record else update.
    """
    if classifier_id == 0:
        # Create new classifier
        db_classifier = models.Classifier(name=classifier.name)
        db.add(db_classifier)
        db.commit()
        db.refresh(db_classifier)
    else:
        # Update existing classifier
        db_classifier = db.query(models.Classifier).filter(models.Classifier.id == classifier_id).first()
        if db_classifier is None:
            raise HTTPException(status_code=404, detail="Classifier not found")
        db_classifier.name = classifier.name
        # Delete existing terms
        db.query(models.ClassifierTerm).filter(models.ClassifierTerm.classifier_id == classifier_id).delete()
        db.commit()
    
    # Add new terms
    for term in classifier.terms:
        db_term = models.ClassifierTerm(**term.dict(), classifier_id=db_classifier.id)
        db.add(db_term)
    db.commit()
    return db_classifier

@router.get("/")
def list_classifiers(db: Session = Depends(get_db)):
    """
    Return the IDs and names of all the classifiers.
    """
    classifiers = db.query(models.Classifier).all()
    return [{"id": c.id, "name": c.name} for c in classifiers]

@router.get("/{classifier_id}")
def get_classifier(classifier_id: int, db: Session = Depends(get_db)):
    """
    Return one classifier record.
    """
    db_classifier = db.query(models.Classifier).filter(models.Classifier.id == classifier_id).first()
    if db_classifier is None:
        raise HTTPException(status_code=404, detail="Classifier not found")
    return db_classifier

@router.get("/run/{classifier_id}/{document_id}")
def run_classifier(classifier_id: int, document_id: int, db: Session = Depends(get_db)):
    """
    Run a classifier against the contents of an uploaded document.
    """
    db_classifier = db.query(models.Classifier).filter(models.Classifier.id == classifier_id).first()
    if db_classifier is None:
        raise HTTPException(status_code=404, detail="Classifier not found")

    document_text = db.query(models.Document).filter(models.Document.id == document_id).first()

    classifications_data = [
        {
            "name": db_classifier.name,
            "terms": [
                {"term": t.term, "distance": t.distance, "weight": t.weight}
                for t in db_classifier.terms
            ],
        }
    ]

    results = document_classifier_simple(document_text.full_texts, classifications_data)
    return results
