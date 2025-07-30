import os
import shutil

from fastapi import UploadFile, HTTPException
from sqlalchemy import and_
from sqlalchemy.orm import Session
from api.util.document_extract import extract, DocumentDecodeException, DocumentUnknownTypeException
from api.models import Document


def upload_document(
        account_id: int,
        db: Session,
        file_upload: UploadFile,
):
    document_storage_dir = load_storage_location(account_id)

    if not os.path.exists(document_storage_dir):
        os.makedirs(document_storage_dir)

    full_path_name = os.path.join(document_storage_dir, file_upload.filename)
    with open(full_path_name, "wb") as buffer:
        shutil.copyfileobj(file_upload.file, buffer)

    try:
        db_document = extract(account_id, full_path_name, db)
    except DocumentDecodeException:
        raise HTTPException(status_code=415, detail="Text cannot be extracted from Document.")
    except DocumentUnknownTypeException:
        raise HTTPException(status_code=415, detail="Document type not supported.")

    return db_document


def remove_document(
    account_id: int,
    document_id,
    db: Session
):
    document = db.query(Document).filter(
        and_(
            Document.id == document_id,
            Document.account_id == account_id,
        )
    ).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    os.remove(str(document.file_name))

    db.delete(document)
    db.commit()

    return


def load_storage_location(account_id:int):
    document_store = os.environ.get("DOCUMENT_STORAGE")
    if not document_store:
        raise HTTPException(status_code=500, detail="DOCUMENT_STORAGE environment variable not set.")

    return os.path.join(document_store, str(account_id))
