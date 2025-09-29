"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please use api.document_extraction.extract instead.

Extract text from a document.
Supports:
    PDF
    txt
    HTML
    docx
    md

Test if the extracted text is actual text and not "subsetted fonts" garbage.
See: https://stackoverflow.com/questions/8039423/pdf-data-extraction-gives-symbols-gibberish

TODO: Integrate https://pypi.org/project/markdrop/ and Dockling to implement PDF -> Markdown
TODO: Find an LLM tuned to understand tables and check-marks
"""

import os
import warnings
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from api import models

# Import from new document extraction package
from api.document_extraction.extract import (
    extract as new_extract,
    DocumentDecodeException,
    DocumentUnknownTypeException
)

# Issue deprecation warning
warnings.warn(
    "api.util.document_extract is deprecated. Use api.document_extraction.extract instead.",
    DeprecationWarning,
    stacklevel=2
)


def extract(user_id: int, file_path_name: str, db: Session) -> models.Document:
    """
    DEPRECATED: Use api.document_extraction.extract instead.

    Extracts text from a document, saves it to the database, and returns the document.
    This is a compatibility wrapper that uses the new document_extraction package.
    """
    # Clean the file name as the old system did
    new_file = clean_file_name(file_path_name)

    try:
        # Use the new document extraction system
        doc = new_extract(new_file)
    except (DocumentDecodeException, DocumentUnknownTypeException):
        # Re-raise the same exceptions for backward compatibility
        raise

    db_wipe(db, new_file)

    # Create a new document record
    db_document = models.Document(file_name=new_file, full_text=doc, account_id=user_id)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document

# Legacy conversion functions - DEPRECATED
# These functions are kept for potential compatibility but are no longer used
# The new document_extraction package handles all conversion logic

def pdf_convert(pdf_file: str) -> tuple:
    """DEPRECATED: Use api.document_extraction.extract instead"""
    warnings.warn("pdf_convert is deprecated", DeprecationWarning, stacklevel=2)
    new_pdf_file = clean_file_name(pdf_file)
    content = new_extract(new_pdf_file)
    return new_pdf_file, content


def html_converter(file_name) -> tuple[str, str]:
    """DEPRECATED: Use api.document_extraction.extract instead"""
    warnings.warn("html_converter is deprecated", DeprecationWarning, stacklevel=2)
    filename = clean_file_name(file_name)
    content = new_extract(filename)
    return filename, content


def docx_converter(file_name) -> tuple[str, str]:
    """DEPRECATED: Use api.document_extraction.extract instead"""
    warnings.warn("docx_converter is deprecated", DeprecationWarning, stacklevel=2)
    filename = clean_file_name(file_name)
    content = new_extract(filename)
    return filename, content


def txt_loader(file_path: str) -> tuple:
    """DEPRECATED: Use api.document_extraction.extract instead"""
    warnings.warn("txt_loader is deprecated", DeprecationWarning, stacklevel=2)
    filename = clean_file_name(file_path)
    content = new_extract(filename)
    return filename, content


def md_loader(file_path: str) -> tuple:
    """DEPRECATED: Use api.document_extraction.extract instead"""
    warnings.warn("md_loader is deprecated", DeprecationWarning, stacklevel=2)
    filename = clean_file_name(file_path)
    content = new_extract(filename)
    return filename, content


def pandoc_convert(file_name: str, type_from: str, exception_message: str = "Document extraction failed") -> str:
    """DEPRECATED: Use api.document_extraction.extract instead"""
    warnings.warn("pandoc_convert is deprecated", DeprecationWarning, stacklevel=2)
    return new_extract(file_name)


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


def find_exe(command_name: str) -> str:
    linux_bin = os.path.join("/usr/bin", command_name)
    osx_brew_bin = os.path.join("/opt/homebrew/bin", command_name)
    if os.path.exists(linux_bin):
        return linux_bin
    if os.path.exists(osx_brew_bin):
        return osx_brew_bin
    raise Exception("Binary program not found: " + command_name)
