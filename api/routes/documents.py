from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api import models
from api.models.database import get_db
from api.util.document_extract import extract, DocumentDecodeException, DocumentUnknownTypeException
from api.dependencies import get_current_user_info
import os
import shutil

router = APIRouter()

@router.post("/")
def create_document(
        db: Session = Depends(get_db),
        file: UploadFile = File(...),
        user = Depends(get_current_user_info)):
    """
    POST endpoint to upload a PDF file in the 'file' field.
    """
    pdf_storage_dir = os.environ.get("PDF_STORAGE")
    if not pdf_storage_dir:
        raise HTTPException(status_code=500, detail="PDF_STORAGE environment variable not set.")

    pdf_storage_dir = os.path.join(pdf_storage_dir, str(user.user_id))

    if not os.path.exists(pdf_storage_dir):
        os.makedirs(pdf_storage_dir)

    file_path = os.path.join(pdf_storage_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        db_document = extract(user.user_id, file_path, db)
    except DocumentDecodeException:
        raise HTTPException(status_code=415, detail="Text cannot be extracted from Document.")
    except DocumentUnknownTypeException:
        raise HTTPException(status_code=415, detail="Document type not supported.")
    return {"id": db_document.id}

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
