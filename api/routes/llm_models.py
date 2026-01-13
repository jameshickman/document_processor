from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from api import models
from api.models.database import get_db
from pydantic import BaseModel
from typing import List, Optional
from api.dependencies import get_current_user_info
from api.util.llm_config import get_api_key_for_provider, is_ollama_enabled

router = APIRouter()


class LLMModelCreate(BaseModel):
    name: str
    provider: str
    model_identifier: str
    base_url: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 2048
    timeout: int = 360
    model_kwargs_json: Optional[str] = None


class LLMModelResponse(BaseModel):
    id: int
    name: str
    provider: str
    model_identifier: str
    base_url: Optional[str]
    temperature: float
    max_tokens: int
    timeout: int
    model_kwargs_json: Optional[str]

    class Config:
        from_attributes = True


@router.get("/configured_providers")
def get_configured_providers(
    user = Depends(get_current_user_info)
):
    """Get list of providers that have API keys configured."""
    configured_providers = []

    # Check OpenAI
    if get_api_key_for_provider("openai"):
        configured_providers.append("openai")

    # Check DeepInfra
    if get_api_key_for_provider("deepinfra"):
        configured_providers.append("deepinfra")

    # Check Ollama (requires explicit enable flag)
    if is_ollama_enabled():
        configured_providers.append("ollama")

    return {"providers": configured_providers}


@router.get("/", response_model=List[LLMModelResponse])
def list_llm_models(
    db: Session = Depends(get_db),
    user = Depends(get_current_user_info)
):
    """List all LLM models for the current user."""
    models_list = db.query(models.LLMModel).filter(
        models.LLMModel.account_id == user.user_id
    ).all()
    return models_list


@router.post("/{model_id}")
def create_or_update_llm_model(
    model_id: int,
    model_data: LLMModelCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user_info)
):
    """Create new model if model_id is 0, else update existing."""
    if model_id == 0:
        # Create new model
        new_model = models.LLMModel(
            name=model_data.name,
            provider=model_data.provider,
            model_identifier=model_data.model_identifier,
            base_url=model_data.base_url,
            temperature=model_data.temperature,
            max_tokens=model_data.max_tokens,
            timeout=model_data.timeout,
            model_kwargs_json=model_data.model_kwargs_json,
            account_id=user.user_id
        )
        db.add(new_model)
        db.commit()
        db.refresh(new_model)
        return {"id": new_model.id}
    else:
        # Update existing model
        db_model = db.query(models.LLMModel).filter(
            and_(
                models.LLMModel.account_id == user.user_id,
                models.LLMModel.id == model_id
            )
        ).first()
        if not db_model:
            raise HTTPException(status_code=404, detail="Model not found")

        # Update fields
        db_model.name = model_data.name
        db_model.provider = model_data.provider
        db_model.model_identifier = model_data.model_identifier
        db_model.base_url = model_data.base_url
        db_model.temperature = model_data.temperature
        db_model.max_tokens = model_data.max_tokens
        db_model.timeout = model_data.timeout
        db_model.model_kwargs_json = model_data.model_kwargs_json

        db.commit()
        return {"id": db_model.id}


@router.get("/{model_id}", response_model=LLMModelResponse)
def get_llm_model(
    model_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user_info)
):
    """Get specific LLM model details."""
    db_model = db.query(models.LLMModel).filter(
        and_(
            models.LLMModel.account_id == user.user_id,
            models.LLMModel.id == model_id
        )
    ).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    return db_model


@router.delete("/{model_id}")
def delete_llm_model(
    model_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user_info)
):
    """Delete an LLM model."""
    db_model = db.query(models.LLMModel).filter(
        and_(
            models.LLMModel.account_id == user.user_id,
            models.LLMModel.id == model_id
        )
    ).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Check if any extractors use this model
    extractors_using = db.query(models.Extractor).filter(
        models.Extractor.llm_model_id == model_id
    ).count()

    if extractors_using > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete model: {extractors_using} extractor(s) are using it"
        )

    db.delete(db_model)
    db.commit()
    return {"success": True}
