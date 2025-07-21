"""
Define a function to convert a PDF file to Markdown text using marker-pdf.
Split the text into chunks under 20000 words, save to the database tables
documents and text_chunks.
"""

import os
import subprocess
from pathlib import Path
from sqlalchemy.orm import Session
from api import models

def pdf_extract(file_path_name: str, db: Session) -> models.Document:
    """
    Extracts text from a PDF, saves it to the database, and returns the document.
    """
    doc = pdf_convert(file_path_name)

    # Create a new document record
    db_document = models.Document(file_name=file_path_name, full_text=doc)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Split the text into chunks and save them
    words = doc.split()
    chunk_size = 20000
    for i in range(0, len(words), chunk_size):
        i_from = i
        if i <= 0:
            i_from = i - 200
        chunk_text = " ".join(words[i_from:i+chunk_size])
        db_chunk = models.TextChunk(chunk=chunk_text, document_id=db_document.id)
        db.add(db_chunk)
    db.commit()

    return db_document

def pdf_convert(pdf_file: str) -> str:
    filename = Path(pdf_file).name
    path = Path(pdf_file).parent
    command = ["/usr/bin/pandoc", "-f pdf", "-t markdown", pdf_file]
    subprocess.run(command)
    md_file = os.path.join(path, filename.split(".")[0] + ".md")
    with open(md_file, "rb") as f:
        content = f.read()
    return str(content)
