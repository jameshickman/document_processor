from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api import models
from api.models.database import get_db
from pydantic import BaseModel
from typing import List
from lib.classifier import document_classifier_simple
from api.dependencies import get_current_user_info
from api.util.import_export import (
    export_classifier_to_yaml, 
    import_classifier_from_yaml,
    create_classifier_set_with_classifiers,
    create_classifiers_with_terms,
    insert_classifier_terms
)

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

@router.post("/import")
async def import_classifier(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Import a classifier set configuration from a YAML file.
    """
    if not file.filename.endswith(('.yaml', '.yml')):
        raise HTTPException(status_code=400, detail="File must be a YAML file (.yaml or .yml)")
    
    try:
        content = await file.read()
        yaml_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")
    
    classifier_set_id = import_classifier_from_yaml(db, yaml_content, user.user_id)
    
    return {"success": True, "classifier_set_id": classifier_set_id, "message": "Classifier imported successfully"}

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
        classifiers_data = [{'name': c.name, 'terms': c.terms} for c in classifier.classifiers]
        classifiers_id = create_classifier_set_with_classifiers(db, classifier.name, user.user_id, classifiers_data)
    else:
        # Update existing classifier
        # First delete associated terms, then classifiers (to avoid foreign key constraint violations)
        classifiers_in_set = db.query(models.Classifier).filter(
            models.Classifier.classifier_set == classifiers_id
        ).all()
        
        for classifier_obj in classifiers_in_set:
            # Delete all terms for this classifier
            db.query(models.ClassifierTerm).filter(
                models.ClassifierTerm.classifier_id == classifier_obj.id
            ).delete()
        
        # Now delete all classifiers in the set
        db.query(models.Classifier).filter(
            models.Classifier.classifier_set == classifiers_id
        ).delete()
        
        db.commit()
        
        # Update the classifier set name
        classifier_set = db.query(models.ClassifierSet).filter(models.ClassifierSet.id == classifiers_id).first()
        classifier_set.name = classifier.name
        db.add(classifier_set)
        db.commit()
        
        # Create new classifiers with their terms
        classifiers_data = [{'name': c.name, 'terms': c.terms} for c in classifier.classifiers]
        create_classifiers_with_terms(db, classifiers_id, classifiers_data)

    return {"id": classifiers_id}


@router.get("/")
def list_classifiers(
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Return the IDs and names of all the classifier sets.
    """
    classifiers = db.query(models.ClassifierSet).filter(models.ClassifierSet.account_id == user.user_id).all()
    return [{"id": c.id, "name": c.name} for c in classifiers]

@router.get("/{classifier_set_id}")
def get_classifier(classifier_set_id: int,
                   db: Session = Depends(get_db),
                   user=Depends(get_current_user_info)):
    """
    Return one classifier record.
    """
    classifier_set = db.query(models.ClassifierSet).filter(
        and_(
            models.ClassifierSet.id == classifier_set_id,
            models.ClassifierSet.account_id == user.user_id
        )
    ).first()

    if classifier_set is None:
        raise HTTPException(status_code=404, detail="Classifier not found")

    classifiers = db.query(models.Classifier).filter(
        models.Classifier.classifier_set == classifier_set.id
    ).all()

    l_c = []

    for classifier in classifiers:
        terms = db.query(models.ClassifierTerm).filter(
            models.ClassifierTerm.classifier_id == classifier.id
        ).all()
        t = []
        for term in terms:
            t.append({
                "term": term.term,
                "distance": term.distance,
                "weight": term.weight
            })
        l_c.append({
            "id": classifier.id,
            "name": classifier.name,
            "terms": t
        })

    return {
        'id': classifier_set.id,
        'name': classifier_set.name,
        'classifiers': l_c
    }

@router.delete("/{classifier_set_id}")
def delete_classifier_set(
        classifier_set_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Delete a classifier set and all its associated classifiers and terms.
    Only allows deletion if the classifier set is owned by the requesting user.
    """
    # Verify ownership before deletion
    classifier_set = db.query(models.ClassifierSet).filter(
        and_(
            models.ClassifierSet.id == classifier_set_id,
            models.ClassifierSet.account_id == user.user_id
        )
    ).first()
    
    if classifier_set is None:
        raise HTTPException(status_code=404, detail="Classifier set not found")
    
    # Delete associated terms first
    classifiers = db.query(models.Classifier).filter(
        models.Classifier.classifier_set == classifier_set_id
    ).all()
    
    for classifier in classifiers:
        # Delete all terms for this classifier
        db.query(models.ClassifierTerm).filter(
            models.ClassifierTerm.classifier_id == classifier.id
        ).delete()
    
    # Delete all classifiers in the set
    db.query(models.Classifier).filter(
        models.Classifier.classifier_set == classifier_set_id
    ).delete()
    
    # Delete the classifier set itself
    db.delete(classifier_set)
    db.commit()
    
    return {"success": True}

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

    document = db.query(models.Document).filter(
        and_(
            models.Document.account_id == user.user_id,
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

    results = document_classifier_simple(document_text, classifications_data)
    
    # Include the document_id in the response so the frontend can match results to files
    response = {
        "document_id": document_id,
        **results
    }
    
    return response

@router.get("/export/{classifier_set_id}")
def export_classifier(
        classifier_set_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Export a classifier set configuration as a YAML file.
    """
    yaml_content = export_classifier_to_yaml(db, classifier_set_id, user.user_id)
    
    # Get the classifier set name for the filename
    classifier_set = db.query(models.ClassifierSet).filter(
        and_(
            models.ClassifierSet.id == classifier_set_id,
            models.ClassifierSet.account_id == user.user_id
        )
    ).first()
    
    if classifier_set is None:
        raise HTTPException(status_code=404, detail="Classifier set not found")
    
    filename = f"{classifier_set.name.replace(' ', '_')}_classifier.yaml"
    
    return PlainTextResponse(
        content=yaml_content,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )