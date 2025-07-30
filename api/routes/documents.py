from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api import models
from api.models.database import get_db
from api.dependencies import get_current_user_info
from api.util.upload_document import upload_document

router = APIRouter()

@router.post("/")
def create_document(
        db: Session = Depends(get_db),
        file: UploadFile = File(...),
        user = Depends(get_current_user_info)):
    document = upload_document(user.user_id, db, file)
    return {"id": document.id}

@router.get("/")
def list_documents(
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Return the IDs and names of all documents.
    """
    documents = db.query(models.Document).filter(models.Document.account_id==user.user_id).all()
    return [{"id": d.id, "name": str(d.file_name).split('/')[-1]} for d in documents]

@router.get("/{document_id}")
def get_document(
        document_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Get the database record for a document.
    """
    db_document = db.query(models.Document).filter(
        and_(
            models.Document.id == document_id,
            models.Document.account_id == user.user_id
        )).first()
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_document
