from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from pydantic import BaseModel

from api.dependencies import get_basic_auth
from api.models import get_db
from api.util.upload_document import upload_document, remove_document
from api.util.document_classify import run_classifier


class RunExtractorRequest(BaseModel):
    extractor_id: int
    file_id: int
    web_hook: str

router = APIRouter()


router.post('/file')
async def upload_file(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    user = Depends(get_basic_auth)
):
    document = upload_document(user.user_id, db, file)
    return {"id": document.id}

router.delete('/file/{file_id}')
async def remove_file(
    file_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    remove_document(user.user_id, file_id, db)
    return {"status": "success"}

router.get('/classifier/{classifier_id}/{file_id}')
async def classifier(
    classifier_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    return run_classifier(user.user_id, file_id, classifier_id, db)

router.post('/extractor/{extractor_id}/{file_id}')
async def extractor(
    extractor_id: int,
    file_id: int,
    request: RunExtractorRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    return {"status": "started"}