from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from api import models
from api.models.database import get_db
from api.util.pdf_extract import pdf_extract
import os
import shutil

router = APIRouter()

@router.post("/")
def create_document(db: Session = Depends(get_db), file: UploadFile = File(...)):
    """
    POST endpoint to upload a PDF file in the 'file' field.
    """
    pdf_storage_dir = os.environ.get("PDF_STORAGE")
    if not pdf_storage_dir:
        raise HTTPException(status_code=500, detail="PDF_STORAGE environment variable not set.")

    if not os.path.exists(pdf_storage_dir):
        os.makedirs(pdf_storage_dir)

    file_path = os.path.join(pdf_storage_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_document = pdf_extract(file_path, db)
    return {"id": db_document.id}

@router.get("/")
def list_documents(db: Session = Depends(get_db)):
    """
    Return the IDs and names of all documents.
    """
    documents = db.query(models.Document).all()
    return [{"id": d.id, "name": d.name} for d in documents]

@router.get("/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    Get the database record for a document.
    """
    db_document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_document
