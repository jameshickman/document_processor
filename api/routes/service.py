from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_

from pydantic import BaseModel

from api.dependencies import get_basic_auth
from api.models import get_db
from api import models
from api.util.upload_document import upload_document, remove_document
from api.util.document_classify import run_classifier
from api.util.extraction_background import run_extractor


class RunExtractorRequest(BaseModel):
    extractor_id: int
    file_id: int
    web_hook: str
    csrf_token: str = ''


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