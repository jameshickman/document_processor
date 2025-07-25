"""
Define a function to convert a PDF file to text using pdftotext.
Test if the extracted text is actual text and not "subsetted fonts" garbage.
See: https://stackoverflow.com/questions/8039423/pdf-data-extraction-gives-symbols-gibberish
"""

import os
import re
import subprocess
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session
from api import models

class PDFDecodeException(Exception):
    pass


def pdf_extract(user_id: int, file_path_name: str, db: Session) -> models.Document:
    """
    Extracts text from a PDF, saves it to the database, and returns the document.
    """
    new_pdf_file, doc = pdf_convert(file_path_name)

    q = text("DELETE FROM documents WHERE file_name = :name")
    db.execute(q, {"name": new_pdf_file})
    db.commit()

    # Create a new document record
    db_document = models.Document(file_name=new_pdf_file, full_text=doc, account_id=user_id)
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
    if content == '' or (not is_real_words(content)):
        raise PDFDecodeException("PDF file cannot be decoded into text")
    return new_pdf_file, content

def is_real_words(word: str) -> bool:
    words = word.split()[0:10]
    if len(words) < 1:
        return False
    for word in words:
        for c in word:
            o = ord(c)
            if o < 33:
                return False
    return True