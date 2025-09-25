from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_

from pydantic import BaseModel

from api.dependencies import get_basic_auth
from api.models import get_db
from api import models
from api.util.upload_document import upload_document, remove_document, upload_markdown_content
from api.util.document_classify import run_classifier
from api.util.extraction_background import run_extractor


class RunExtractorRequest(BaseModel):
    extractor_id: int
    file_id: int
    web_hook: str
    csrf_token: str = ''


class MarkdownUploadRequest(BaseModel):
    content: str


router = APIRouter()


@router.post('/file')
async def upload_file(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    user = Depends(get_basic_auth)
):
    document = upload_document(user.user_id, db, file)
    return {"id": document.id}

@router.delete('/file/{file_id}')
async def remove_file(
    file_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    remove_document(user.user_id, file_id, db)
    return {"status": "success"}


@router.put('/file/markdown')
async def upload_markdown(
    request: MarkdownUploadRequest,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    """
    Upload Markdown content as a document.
    The first line of the content should be used as the filename.
    """
    result = upload_markdown_content(user.user_id, db, request.content)
    return {"id": result["document"].id, "filename": result["filename"]}

@router.get('/classifier/{classifier_id}/{file_id}')
async def classifier(
    classifier_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    return run_classifier(user.user_id, file_id, classifier_id, db)

@router.post('/extractor')
async def extractor(
    request: RunExtractorRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    # Verify that the specified extractor exists and belongs to the user
    db_extractor = db.query(models.Extractor).filter(
        and_(
            models.Extractor.id == request.extractor_id,
            models.Extractor.account_id == user.user_id
        )
    ).first()
    
    if not db_extractor:
        raise HTTPException(status_code=404, detail="Extractor not found")
    
    # Verify that the specified file exists and belongs to the user
    document = db.query(models.Document).filter(
        and_(
            models.Document.id == request.file_id,
            models.Document.account_id == user.user_id
        )
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Verify that the document has content to extract from
    if not document.full_text:
        raise HTTPException(status_code=400, detail="Document has no content available for extraction")
    
    background_tasks.add_task(
        run_extractor,
        user.user_id,
        request.extractor_id,
        request.file_id,
        db,
        request.web_hook,
        request.csrf_token
    )
    return {"status": "started"}

@router.get('/marked-pdf/{extractor_id}/{file_id}')
async def download_marked_pdf(
    extractor_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    """
    Download the marked-up PDF version of a document created during extraction.
    The PDF will have citations highlighted based on the extraction results.
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
            models.Document.id == file_id
        )
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="File not found")

    # Determine the source PDF path (may be original or converted)
    source_file = document.file_name
    
    # If the original file is not a PDF, check if a converted version exists
    if not source_file.lower().endswith('.pdf'):
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
        raise HTTPException(
            status_code=500, 
            detail="Error retrieving marked-up document. Please try running extraction again."
        )

@router.get('/marked-pdf-status/{file_id}')
async def get_marked_pdf_status(
    file_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    """
    Get the status of available marked-up versions for a document across all user's extractors.
    Returns information about which extractors have created marked versions.
    """
    from api.pdf_markup.highlight_pdf import get_marked_files
    import os
    
    document = db.query(models.Document).filter(
        and_(
            models.Document.account_id == user.user_id,
            models.Document.id == file_id
        )
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="File not found")

    # Determine the source PDF path
    source_file = document.file_name
    
    # If the original file is not a PDF, check if a converted version exists
    if not source_file.lower().endswith('.pdf'):
        potential_pdf = os.path.splitext(source_file)[0] + '.pdf'
        if os.path.exists(potential_pdf):
            source_file = potential_pdf
        else:
            return {
                "file_id": file_id,
                "pdf_available": False,
                "marked_versions": [],
                "message": "Document needs to be converted to PDF first"
            }
    
    # Get all marked files for this document
    try:
        all_marked_files = get_marked_files(source_file)
        
        # Parse extractor IDs from filenames and filter by user's extractors
        marked_versions = []
        user_extractors = db.query(models.Extractor).filter(
            models.Extractor.account_id == user.user_id
        ).all()
        user_extractor_ids = {e.id for e in user_extractors}
        
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
                            
                            # Only include if this extractor belongs to the user
                            if extractor_id in user_extractor_ids:
                                # Get extractor name
                                extractor = next((e for e in user_extractors if e.id == extractor_id), None)
                                
                                marked_versions.append({
                                    "extractor_id": extractor_id,
                                    "extractor_name": extractor.name if extractor else f"Unknown (ID: {extractor_id})",
                                    "file_size": os.path.getsize(marked_file)
                                })
                    except (ValueError, IndexError):
                        # Skip files that don't match expected pattern
                        continue
        
        return {
            "file_id": file_id,
            "pdf_available": True,
            "marked_versions": marked_versions,
            "total_marked_versions": len(marked_versions)
        }
        
    except Exception as e:
        return {
            "file_id": file_id,
            "pdf_available": True,
            "marked_versions": [],
            "error": "Error retrieving marked version information"
        }

@router.get('/classifiers')
async def get_classifiers(
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    """
    List all classifier sets belonging to the authenticated user.
    Returns names and IDs of classifier sets.
    """
    classifier_sets = db.query(models.ClassifierSet).filter(
        models.ClassifierSet.account_id == user.user_id
    ).all()

    return [{"id": cs.id, "name": cs.name} for cs in classifier_sets]

@router.get('/extractors')
async def get_extractors(
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    """
    List all extractors belonging to the authenticated user.
    Returns names and IDs of extractors.
    """
    extractors = db.query(models.Extractor).filter(
        models.Extractor.account_id == user.user_id
    ).all()

    return [{"id": e.id, "name": e.name} for e in extractors]
