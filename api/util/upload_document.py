import os
import shutil
import re
from pathlib import Path

from fastapi import UploadFile, HTTPException
from sqlalchemy import and_, text
from sqlalchemy.orm import Session

# Option 1: Keep using deprecated wrapper (shows deprecation warnings)
from api.util.document_extract import extract, DocumentDecodeException, DocumentUnknownTypeException

# Option 2: Use new system directly (recommended for new code)
# from api.document_extraction.extract import extract as new_extract, DocumentDecodeException, DocumentUnknownTypeException

from api.models import Document

# Migration Guide:
# To fully migrate from the deprecated api.util.document_extract:
#
# 1. Replace the imports above with:
#    from api.document_extraction.extract import extract as new_extract, DocumentDecodeException, DocumentUnknownTypeException
#
# 2. Replace extract() calls with new_extract_with_db():
#    def new_extract_with_db(user_id: int, file_path_name: str, db: Session) -> Document:
#        # Clean filename (preserving legacy behavior)
#        filename = Path(file_path_name).name.replace(" ", "_")
#        if filename != Path(file_path_name).name:
#            path = Path(file_path_name).parent
#            new_file = os.path.join(path, filename)
#            if os.path.exists(new_file):
#                os.remove(new_file)
#            os.rename(file_path_name, new_file)
#            file_path_name = new_file
#
#        # Extract content using new system
#        doc = new_extract(file_path_name)
#
#        # Clean up existing records
#        q = text("DELETE FROM documents WHERE file_name = :name")
#        db.execute(q, {"name": file_path_name})
#        db.commit()
#
#        # Create new document record
#        db_document = Document(file_name=file_path_name, full_text=doc, account_id=user_id)
#        db.add(db_document)
#        db.commit()
#        db.refresh(db_document)
#        return db_document


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


def upload_markdown_content(
    account_id: int,
    db: Session,
    content: str,
):
    """
    Upload markdown content as a document.
    The first line of the content is used as the filename.
    """
    content = content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    lines = content.split('\n')
    first_line = lines[0].strip()

    # Extract filename from first line, removing markdown formatting if present
    filename = first_line.lstrip('#').strip()

    # Sanitize filename (remove invalid characters)
    filename = re.sub(r'[^\w\s-]', '', filename).strip()
    filename = re.sub(r'[-\s]+', '-', filename)

    if not filename:
        filename = "untitled"

    # Ensure .md extension
    if not filename.lower().endswith('.md'):
        filename += '.md'

    # Use the same storage location as regular uploads
    document_storage_dir = load_storage_location(account_id)

    if not os.path.exists(document_storage_dir):
        os.makedirs(document_storage_dir)

    full_path_name = os.path.join(document_storage_dir, filename)

    # Write content to file
    with open(full_path_name, 'w', encoding='utf-8') as f:
        f.write(content)

    try:
        db_document = extract(account_id, full_path_name, db)
        return {"document": db_document, "filename": filename}
    except DocumentDecodeException:
        # Clean up file if extraction fails
        if os.path.exists(full_path_name):
            os.remove(full_path_name)
        raise HTTPException(status_code=415, detail="Text cannot be extracted from Document.")
    except DocumentUnknownTypeException:
        # Clean up file if extraction fails
        if os.path.exists(full_path_name):
            os.remove(full_path_name)
        raise HTTPException(status_code=415, detail="Document type not supported.")
    except Exception as e:
        # Clean up file if extraction fails
        if os.path.exists(full_path_name):
            os.remove(full_path_name)
        raise HTTPException(status_code=500, detail=f"Failed to process markdown file: {str(e)}")


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
