"""
Define a function to convert a document file to text using pdftotext.
Supports:
    PDF
    txt
    HTML
    docx

Test if the extracted text is actual text and not "subsetted fonts" garbage.
See: https://stackoverflow.com/questions/8039423/pdf-data-extraction-gives-symbols-gibberish
"""

import os
import subprocess
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session
from api import models

class DocumentDecodeException(Exception):
    pass


class DocumentUnknownTypeException(Exception):
    pass


def extract(user_id: int, file_path_name: str, db: Session) -> models.Document:
    """
    Extracts text from a document, saves it to the database, and returns the document.
    """
    file_type = Path(file_path_name).suffix.lower()
    if file_type == ".pdf":
        new_file, doc = pdf_convert(file_path_name)
    elif file_type == ".txt":
        new_file, doc = txt_loader(file_path_name)
    elif file_type == ".html" or file_type == ".htm":
        new_file, doc = html_converter(file_path_name)
    elif file_type == ".docx":
        new_file, doc = docx_converter(file_path_name)
    else:
        raise DocumentUnknownTypeException("Document type not supported")

    db_wipe(db, new_file)

    # Create a new document record
    db_document = models.Document(file_name=new_file, full_text=doc, account_id=user_id)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document

def pdf_convert(pdf_file: str) -> tuple:
    new_pdf_file = clean_file_name(pdf_file)
    command = ["/usr/bin/pdftotext", new_pdf_file, "-"]
    result = subprocess.run(command, capture_output=True)
    content = str(result.stdout.decode("utf-8").replace("\n", " "))
    if content == '' or (not is_real_words(content)):
        raise DocumentDecodeException("PDF file cannot be decoded into text")
    return new_pdf_file, content


def html_converter(file_name) -> tuple[str, str]:
    filename = clean_file_name(file_name)
    content = pandoc_convert(filename, "html", "No text could be extracted from HTML file")
    return filename, content


def docx_converter(file_name) -> tuple[str, str]:
    filename = clean_file_name(file_name)
    content = pandoc_convert(filename, "docx", "No text could be extracted from DOCX file")
    return filename, content


def pandoc_convert(file_name: str, type_from: str, exception_message: str = "Document extraction failed") -> str:
    command = ["/usr/bin/pandoc", file_name, "-f", type_from, "-t", "markdown"]
    result = subprocess.run(command, capture_output=True)
    content = str(result.stdout.decode("utf-8").replace("\n", " "))
    if content == '' or (not is_real_words(content)):
        raise DocumentDecodeException(exception_message)
    return content


def txt_loader(file_path: str) -> tuple:
    filename = clean_file_name(file_path)
    f = open(filename, 'r')
    content = f.read()
    return filename, content


def clean_file_name(file_name) -> str:
    filename = Path(file_name).name
    filename_clean = filename.replace(" ", "_")
    if filename_clean == filename:
        return file_name
    path = Path(file_name).parent
    new_file = os.path.join(path, filename_clean)
    if os.path.exists(new_file):
        os.remove(new_file)
    os.rename(file_name, new_file)
    return new_file


def db_wipe(db: Session, file_name: str):
    q = text("DELETE FROM documents WHERE file_name = :name")
    db.execute(q, {"name": file_name})
    db.commit()


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