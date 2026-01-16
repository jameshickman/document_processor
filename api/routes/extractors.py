from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api import models
from api.models.database import get_db
from pydantic import BaseModel
from typing import List, Optional
from api.util.llm_config import llm_config
from api.util.extraction_core import run_extractor_with_markup
from api.dependencies import get_current_user_info
from api.util.import_export import (
    export_extractor_to_yaml, 
    import_extractor_from_yaml,
    create_extractor_with_fields,
    create_extractor_fields
)

router = APIRouter()

class ExtractorField(BaseModel):
    name: str
    description: str

class Extractor(BaseModel):
    name: str
    prompt: str
    fields: List[ExtractorField]
    llm_model_id: Optional[int] = None

@router.post("/import")
async def import_extractor(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Import an extractor configuration from a YAML file.
    """
    if not file.filename.endswith(('.yaml', '.yml')):
        raise HTTPException(status_code=400, detail="File must be a YAML file (.yaml or .yml)")
    
    try:
        content = await file.read()
        yaml_content = content.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")
    
    extractor_id = import_extractor_from_yaml(db, yaml_content, user.user_id)
    
    return {"success": True, "extractor_id": extractor_id, "message": "Extractor imported successfully"}

@router.post("/{extractor_id}")
def create_or_update_extractor(
        extractor_id: int,
        extractor: Extractor,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    If the extractor_id is 0, create a new record else update.
    """
    if extractor_id == 0:
        # Create new extractor
        fields_data = [{'name': f.name, 'description': f.description} for f in extractor.fields]
        extractor_id = create_extractor_with_fields(db, extractor.name, extractor.prompt, user.user_id, fields_data, extractor.llm_model_id)
        return {"id": extractor_id}
    else:
        # Update existing extractor
        db_extractor = db.query(models.Extractor).filter(
            and_(
                models.Extractor.account_id == user.user_id,
                models.Extractor.id == extractor_id
            )
        ).first()
        if db_extractor is None:
            raise HTTPException(status_code=404, detail="Extractor not found")
        db_extractor.name = extractor.name
        db_extractor.prompt = extractor.prompt
        db_extractor.llm_model_id = extractor.llm_model_id
        # Delete existing fields
        db.query(models.ExtractorField).filter(models.ExtractorField.extractor_id == extractor_id).delete()
        db.commit()
        
        # Add new fields using utility function
        fields_data = [{'name': f.name, 'description': f.description} for f in extractor.fields]
        create_extractor_fields(db, db_extractor.id, fields_data)
        
    return {"id": db_extractor.id}

@router.get("/")
def list_extractors(
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Return the IDs and names of all the extractors.
    """
    extractors = db.query(models.Extractor).filter(models.Extractor.account_id == user.user_id).all()
    return [{"id": e.id, "name": e.name} for e in extractors]

@router.get("/{extractor_id}")
def get_extractor(
        extractor_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    db_extractor = db.query(models.Extractor).filter(
        and_(
            models.Extractor.account_id == user.user_id,
            models.Extractor.id == extractor_id
        )
    ).first()
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")
    return {
        "name": db_extractor.name,
        "id": db_extractor.id,
        "prompt": db_extractor.prompt,
        "llm_model_id": db_extractor.llm_model_id,
        "fields": [{"name": field.name, "description": field.description} for field in db_extractor.fields]
    }

@router.delete("/{extractor_id}")
def delete_extractor(
        extractor_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Delete an extractor and its associated fields.
    """
    db_extractor = db.query(models.Extractor).filter(
        and_(
            models.Extractor.account_id == user.user_id,
            models.Extractor.id == extractor_id
        )
    ).first()
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")
    
    # Delete associated fields first (cascade should handle this, but being explicit)
    db.query(models.ExtractorField).filter(models.ExtractorField.extractor_id == extractor_id).delete()
    
    # Delete the extractor
    db.delete(db_extractor)
    db.commit()
    return {"success": True}

from fastapi import Request

@router.get("/run/{extractor_id}/{document_id}")
def run_extractor(
        request: Request,
        extractor_id: int,
        document_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Run an extractor against the contents of a document and create a marked-up PDF with highlighted citations.
    """
    from api.util.source_detection import detect_source_type

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
        raise HTTPException(status_code=404, detail="Document not found or has no content")

    # Run extractor with markup using shared utility
    execution_result = run_extractor_with_markup(
        document_text=document.full_text,
        document_file_path=document.file_name,
        extractor_prompt=db_extractor.prompt,
        extractor_fields={field.name: field.description for field in db_extractor.fields},
        extractor_id=extractor_id,
        llm_config=llm_config,
        use_logging=False,  # Use print statements in API routes
        db=db,
        document_id=document_id,
        use_vector_search=True,
        llm_model_id=db_extractor.llm_model_id,
        account_id=user.user_id,
        source_type=detect_source_type(request),
        user_agent=request.headers.get('User-Agent'),
        ip_address=request.client.host
    )

    # Return the extraction result with marked PDF info
    response_data = {
        "id": extractor_id,
        "document_id": document_id,
        "result": execution_result.extraction_result,
        "marked_pdf_available": execution_result.marked_pdf_available
    }

    if execution_result.marked_pdf_path:
        response_data["marked_pdf_path"] = execution_result.marked_pdf_path

    return response_data


@router.get("/export/{extractor_id}")
def export_extractor(
        extractor_id: int,
        db: Session = Depends(get_db),
        user = Depends(get_current_user_info)):
    """
    Export an extractor configuration as a YAML file.
    """
    yaml_content = export_extractor_to_yaml(db, extractor_id, user.user_id)
    
    # Get the extractor name for the filename
    db_extractor = db.query(models.Extractor).filter(
        and_(
            models.Extractor.id == extractor_id,
            models.Extractor.account_id == user.user_id
        )
    ).first()
    
    if db_extractor is None:
        raise HTTPException(status_code=404, detail="Extractor not found")
    
    filename = f"{db_extractor.name.replace(' ', '_')}_extractor.yaml"
    
    return PlainTextResponse(
        content=yaml_content,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )