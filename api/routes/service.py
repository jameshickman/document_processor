from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from pydantic import BaseModel

from api.dependencies import get_basic_auth
from api.models import get_db


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
    return {}

router.delete('/file/{file_id}')
async def remove_file(
    file_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    return {}

router.get('/classifier/{classifier_id}/{file_id}')
async def run_classifier(
    classifier_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    return {}

router.post('/extractor/{extractor_id}/{file_id}')
async def run_extractor(
    extractor_id: int,
    file_id: int,
    request: RunExtractorRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user = Depends(get_basic_auth)
):
    return {}