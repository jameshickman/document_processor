from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api import models
from api.models.database import get_db
from pydantic import BaseModel
from typing import List
from lib.classifier import document_classifier_simple
from api.dependencies import get_current_user_info

router = APIRouter()

class ClassifierTerm(BaseModel):
    term: str
    distance: int
    weight: float

class Classifier(BaseModel):
    name: str
    terms: List[ClassifierTerm]

class Classifiers(BaseModel):
    name: str
    classifiers: List[Classifier]

@router.post("/{classifiers_id}")
def create_or_update_classifier(
        classifiers_id: int,
        classifier: Classifiers,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    If the classifier_id is 0, create a new record else update.
    """
    if classifiers_id == 0:
        # Create new classifier set
        classifier_set = models.ClassifierSet(
            name=classifier.name,
            account_id=user.user_id
        )
        db.add(classifier_set)
        db.commit()
        db.refresh(classifier_set)
        set_id = classifier_set.id
        create_doc_classes_set(db, set_id, classifier.classifiers)
        classifiers_id = classifier_set.id
    else:
        # Update existing classifier
        q = text("DELETE FROM classifiers WHERE classifier_set = :id")
        db.execute(q, {"id": classifiers_id})
        db.commit()
        classifier_set = db.query(models.Classifier).filter(models.Classifier.id == classifiers_id).first()
        classifier_set.name = classifier.name
        db.add(classifier_set)
        db.commit()
        create_doc_classes_set(db, classifiers_id, classifier.classifiers)

    return {"id": classifiers_id}

def create_doc_classes_set(db: Session, set_id: int, doc_classes: list[Classifier]):
    for doc_type in doc_classes:
        doc_classification = models.Classifier()
        doc_classification.name = doc_type.name
        doc_classification.classifier_set = set_id
        db.add(doc_classification)
        db.commit()
        insert_terms(db, doc_classification.id, doc_type.terms)
    pass

def insert_terms(db: Session, doc_class_id: int, terms: List[ClassifierTerm]):
    for term in terms:
        classifier_term = models.ClassifierTerm(term=term.term, distance=term.distance, weight=term.weight, classifier_id=doc_class_id)
        db.add(classifier_term)
        db.commit()
    pass

@router.get("/")
def list_classifiers(
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Return the IDs and names of all the classifier sets.
    """
    classifiers = db.query(models.ClassifierSets).filter(models.ClassifierSet.account_id == user.user_id).all()
    return [{"id": c.id, "name": c.name} for c in classifiers]

@router.get("/{classifier_set_id}")
def get_classifier(classifier_set_id: int,
                   db: Session = Depends(get_db),
                   user=Depends(get_current_user_info)):
    """
    Return one classifier record.
    """
    db_classifier = db.query(models.ClassifierSet).filter(
        and_(
            models.ClassifierSet.id == classifier_set_id,
            models.ClassifierSet.account_id == user.user_id
        )
    ).first()
    if db_classifier is None:
        raise HTTPException(status_code=404, detail="Classifier not found")
    return db_classifier

@router.get("/run/{classifier_set_id}/{document_id}")
def run_classifier(
        classifier_set_id: int, document_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Run a classifier against the contents of an uploaded document.
    """
    # Verify that the user owns the specified Classifier Set
    classifier_set = db.query(models.ClassifierSet).filter(
        and_(
            models.ClassifierSet.id == classifier_set_id,
            models.ClassifierSet.account_id == user.user_id
        )
    ).first()

    if not classifier_set:
        raise HTTPException(status_code=404, detail="Classifier not found")

    classifiers = db.query(models.Classifier).filter(models.Classifier.classifier_set == classifier_set_id).all()
    if classifiers is None:
        raise HTTPException(status_code=404, detail="Classifier Set not found")

    document_text = db.query(models.Document).filter(
        and_(
            models.Document.account_id == user.user_id,
            models.Document.id == document_id
        )
    ).first()

    if not document_text:
        raise HTTPException(status_code=404, detail="Document not found")

    classifications_data = []

    for classifier in classifiers:
        d_classifier = {
            "name": classifier.name,
            "terms": [],
        }
        terms = db.query(models.ClassifierTerm).filter(models.ClassifierTerm.classifier_id == classifier.id).all()
        for term in terms:
            d_classifier["terms"].append({
                "term": term.term,
                "distance": term.distance,
                "weight": term.weight
            })
        classifications_data.append(d_classifier)

    results = document_classifier_simple(document_text.full_text, classifications_data)
    return results
