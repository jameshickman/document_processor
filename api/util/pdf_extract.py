"""
Define a function to convert a PDF file to Markdown text using marker-pdf.
Split the text into chunks under 20000 words, save to the database tables
documents and text_chunks.
"""

import marker
from sqlalchemy.orm import Session
from .. import models

def pdf_extract(file_path: str, db: Session) -> models.Document:
    """
    Extracts text from a PDF, saves it to the database, and returns the document.
    """
    doc, _ = marker.convert_single_pdf(file_path)

    # Create a new document record
    db_document = models.Document(file_name=file_path)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Split the text into chunks and save them
    words = doc.split()
    chunk_size = 20000
    for i in range(0, len(words), chunk_size):
        chunk_text = " ".join(words[i:i+chunk_size])
        db_chunk = models.TextChunk(chunk=chunk_text, document_id=db_document.id)
        db.add(db_chunk)
    db.commit()

    return db_document
