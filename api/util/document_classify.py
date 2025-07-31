from fastapi import HTTPException

from api import models
from api.models.database import get_db
from lib.classifier import document_classifier_simple
from sqlalchemy.orm import Session
from sqlalchemy import and_


def run_classifier(
    user_id: int,
    document_id: int,
    classifier_set_id: int,
    db: Session
):
    classifier_set = db.query(models.ClassifierSet).filter(
        and_(
            models.ClassifierSet.id == classifier_set_id,
            models.ClassifierSet.account_id == user_id
        )
    ).first()

    if not classifier_set:
        raise HTTPException(status_code=404, detail="Classifier not found")

    classifiers = db.query(models.Classifier).filter(models.Classifier.classifier_set == classifier_set_id).all()
    if classifiers is None:
        raise HTTPException(status_code=404, detail="Classifier Set not found")

    document = db.query(models.Document).filter(
        and_(
            models.Document.account_id == user_id,
            models.Document.id == document_id
        )
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    document_text = str(document.full_text)

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

    return document_classifier_simple(document_text, classifications_data)
