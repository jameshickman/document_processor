"""
Define a function to convert a PDF file to Markdown text using marker-pdf.
Split the text into chunks under CHUNK_SIZE words, save to the database tables
documents and text_chunks.
"""

import os
import subprocess
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session
from api import models

CHUNK_SIZE = 1800

def pdf_extract(file_path_name: str, db: Session) -> models.Document:
    """
    Extracts text from a PDF, saves it to the database, and returns the document.
    """
    new_pdf_file, doc = pdf_convert(file_path_name)

    q = text("DELETE FROM documents WHERE file_name = :name")
    db.execute(q, {"name": new_pdf_file})
    db.commit()

    # Create a new document record
    db_document = models.Document(file_name=new_pdf_file, full_text=doc)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document

def pdf_convert(pdf_file: str) -> tuple:
    filename = Path(pdf_file).name
    filename_clean = filename.replace(" ", "_")
    path = Path(pdf_file).parent
    new_pdf_file = os.path.join(path, filename_clean)
    if os.path.exists(new_pdf_file):
        os.remove(new_pdf_file)
    os.rename(pdf_file, new_pdf_file)
    command = ["/usr/bin/pdftotext", new_pdf_file, "-"]
    result = subprocess.run(command, capture_output=True)
    content = str(result.stdout.decode("utf-8").replace("\n", " "))
    return new_pdf_file, content
