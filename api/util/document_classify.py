import time
from fastapi import HTTPException

from api import models
from lib.classifier import document_classifier_simple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api.services.usage_tracker import UsageTracker


def run_classifier(
    user_id: int,
    document_id: int,
    classifier_set_id: int,
    db: Session
):
    start_time = time.time()

    try:
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

        result = document_classifier_simple(document_text, classifications_data)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log successful classification
        try:
            from api.services.usage_tracker import UsageTracker
            tracker = UsageTracker(db)
            tracker.log_classification_sync(
                account_id=user_id,
                document_id=document_id,
                classifier_id=classifier_set_id,
                duration_ms=duration_ms,
                status='success',
                source_type='api'  # This endpoint is API-only
            )
        except Exception as e:
            # Log the error but don't crash the main operation
            import logging
            logging.error(f"Failed to log classification: {str(e)}")

        return result

    except Exception as e:
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log failed classification
        try:
            from api.services.usage_tracker import UsageTracker
            tracker = UsageTracker(db)
            tracker.log_classification_sync(
                account_id=user_id,
                document_id=document_id,
                classifier_id=classifier_set_id,
                duration_ms=duration_ms,
                status='failure',
                error_message=str(e),
                source_type='api'  # This endpoint is API-only
            )
        except Exception as e_log:
            # Log the error but don't crash the main operation
            import logging
            logging.error(f"Failed to log classification error: {str(e_log)}")

        raise
