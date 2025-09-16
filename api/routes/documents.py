from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api import models
from api.models.database import get_db
from api.dependencies import get_current_user_info
from api.util.upload_document import upload_document
import os

router = APIRouter()

@router.post("/")
def create_document(
        db: Session = Depends(get_db),
        file: UploadFile = File(...),
        user = Depends(get_current_user_info)):
    document = upload_document(user.user_id, db, file)
    return {"id": document.id}

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

@router.get("/marked/{extractor_id}/{document_id}")
def download_marked_up_version(
    extractor_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user_info)
):
    """
    If a marked-up version of the file exists, return the PDF file for download.
    """
    from fastapi.responses import FileResponse
    from api.pdf_markup.highlight_pdf import get_marked_files
    import os
    
    # Verify user has access to both the extractor and document
    db_extractor = db.query(models.Extractor).filter(
        and_(
            models.Extractor.account_id == user.user_id,
            models.Extractor.id == extractor_id
        )
    ).first()
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")

    document = db.query(models.Document).filter(
        and_(
            models.Document.account_id == user.user_id,
            models.Document.id == document_id
        )
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Determine the source PDF path (may be original or converted)
    source_file = document.file_name
    
    # If the original file is not a PDF, check if a converted version exists
    if not source_file.lower().endswith('.pdf'):
        # Check for a converted PDF in the same directory
        potential_pdf = os.path.splitext(source_file)[0] + '.pdf'
        if os.path.exists(potential_pdf):
            source_file = potential_pdf
        else:
            raise HTTPException(
                status_code=404, 
                detail="No PDF version available for this document. Run extraction first to generate marked version."
            )
    
    # Get marked files for this specific extractor and document
    try:
        marked_files = get_marked_files(source_file, extractor_id=extractor_id)
        
        if not marked_files:
            raise HTTPException(
                status_code=404, 
                detail="No marked-up version found. Run extraction first to generate marked version."
            )
        
        # Use the first (and should be only) marked file for this extractor
        marked_file_path = marked_files[0]
        
        if not os.path.exists(marked_file_path):
            raise HTTPException(
                status_code=404, 
                detail="Marked-up file was found in index but file no longer exists on disk."
            )
        
        # Generate a user-friendly filename for download
        base_name = os.path.splitext(os.path.basename(source_file))[0]
        download_filename = f"{base_name}_marked_extractor_{extractor_id}.pdf"
        
        return FileResponse(
            path=marked_file_path,
            filename=download_filename,
            media_type="application/pdf"
        )
        
    except Exception as e:
        # Log the error for debugging but return user-friendly message
        print(f"Error retrieving marked file: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error retrieving marked-up document. Please try running extraction again."
        )

@router.get("/marked-status/{document_id}")
def get_marked_document_status(
    document_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user_info)
):
    """
    Get the status of available marked-up versions for a document across all extractors.
    """
    from api.pdf_markup.highlight_pdf import get_marked_files
    import os
    
    document = db.query(models.Document).filter(
        and_(
            models.Document.account_id == user.user_id,
            models.Document.id == document_id
        )
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Determine the source PDF path
    source_file = document.file_name
    
    # If the original file is not a PDF, check if a converted version exists
    if not source_file.lower().endswith('.pdf'):
        potential_pdf = os.path.splitext(source_file)[0] + '.pdf'
        if os.path.exists(potential_pdf):
            source_file = potential_pdf
        else:
            return {
                "document_id": document_id,
                "pdf_available": False,
                "marked_versions": [],
                "message": "Document needs to be converted to PDF first"
            }
    
    # Get all marked files for this document
    try:
        all_marked_files = get_marked_files(source_file)
        
        # Parse extractor IDs from filenames
        marked_versions = []
        for marked_file in all_marked_files:
            if os.path.exists(marked_file):
                # Extract extractor_id from filename pattern: name.marked.{extractor_id}.pdf
                filename = os.path.basename(marked_file)
                if '.marked.' in filename:
                    try:
                        parts = filename.split('.marked.')
                        if len(parts) >= 2:
                            extractor_id_part = parts[1].split('.pdf')[0]
                            extractor_id = int(extractor_id_part)
                            
                            # Get extractor name if it exists and belongs to user
                            extractor = db.query(models.Extractor).filter(
                                and_(
                                    models.Extractor.id == extractor_id,
                                    models.Extractor.account_id == user.user_id
                                )
                            ).first()
                            
                            marked_versions.append({
                                "extractor_id": extractor_id,
                                "extractor_name": extractor.name if extractor else f"Unknown (ID: {extractor_id})",
                                "file_path": marked_file,
                                "file_size": os.path.getsize(marked_file)
                            })
                    except (ValueError, IndexError):
                        # Skip files that don't match expected pattern
                        continue
        
        return {
            "document_id": document_id,
            "pdf_available": True,
            "marked_versions": marked_versions,
            "total_marked_versions": len(marked_versions)
        }
        
    except Exception as e:
        print(f"Error getting marked document status: {e}")
        return {
            "document_id": document_id,
            "pdf_available": True,
            "marked_versions": [],
            "error": "Error retrieving marked version information"
        }

@router.delete("/{document_id}")
def delete_document(
        document_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Delete a document and its associated files, including any marked-up versions.
    """
    from api.pdf_markup.highlight_pdf import get_marked_files
    
    db_document = db.query(models.Document).filter(
        and_(
            models.Document.id == document_id,
            models.Document.account_id == user.user_id
        )).first()
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    files_deleted = []
    files_failed = []
    
    # Delete the original file if it exists
    if db_document.file_name and os.path.exists(db_document.file_name):
        try:
            os.remove(db_document.file_name)
            files_deleted.append(db_document.file_name)
        except OSError as e:
            print(f"Warning: Could not delete file {db_document.file_name}: {e}")
            files_failed.append(db_document.file_name)
    
    # Delete converted PDF if it exists (for non-PDF originals)
    if not db_document.file_name.lower().endswith('.pdf'):
        potential_pdf = os.path.splitext(db_document.file_name)[0] + '.pdf'
        if os.path.exists(potential_pdf):
            try:
                os.remove(potential_pdf)
                files_deleted.append(potential_pdf)
            except OSError as e:
                print(f"Warning: Could not delete converted PDF {potential_pdf}: {e}")
                files_failed.append(potential_pdf)
    
    # Delete all marked-up versions
    try:
        source_file = db_document.file_name
        if not source_file.lower().endswith('.pdf'):
            potential_pdf = os.path.splitext(source_file)[0] + '.pdf'
            if os.path.exists(potential_pdf):
                source_file = potential_pdf
        
        marked_files = get_marked_files(source_file)
        for marked_file in marked_files:
            if os.path.exists(marked_file):
                try:
                    os.remove(marked_file)
                    files_deleted.append(marked_file)
                except OSError as e:
                    print(f"Warning: Could not delete marked file {marked_file}: {e}")
                    files_failed.append(marked_file)
    except Exception as e:
        print(f"Warning: Error while cleaning up marked files: {e}")
    
    # Delete the database record
    db.delete(db_document)
    db.commit()
    
    return {
        "success": True,
        "files_deleted": len(files_deleted),
        "files_failed": len(files_failed),
        "deleted_files": files_deleted if files_deleted else None,
        "failed_files": files_failed if files_failed else None
    }
