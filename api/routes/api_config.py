import uuid
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.models.database import get_db
from api.models.accounts import Account
from api.dependencies import get_current_user_info, User

router = APIRouter()

class ApiKeyResponse(BaseModel):
    api_key: str
    api_secret: str


class ApiKeyUpdateResponse(BaseModel):
    api_key: str
    api_secret: str
    message: str


def generate_api_key() -> str:
    """Generate a new API key in the format 'smolminds-docprocessor-' + UUID4"""
    return f"smolminds-docprocessor-{uuid.uuid4()}"


def generate_api_secret() -> str:
    """Generate a 128-character random API secret"""
    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(secrets.choice(characters) for _ in range(128))


def get_user_account(current_user: User, db: Session) -> Account:
    """Get user account from database with error handling"""
    account = db.query(Account).filter(Account.id == current_user.user_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account


def ensure_api_credentials(account: Account, db: Session) -> tuple[str, str]:
    """Ensure account has API credentials, creating them if missing"""
    if not account.api_key or not account.api_secret:
        try:
            account.api_key = generate_api_key()
            account.api_secret = generate_api_secret()
            db.commit()
            db.refresh(account)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create API credentials: {str(e)}")
    
    return account.api_key, account.api_secret


def update_api_credentials(account: Account, db: Session) -> tuple[str, str]:
    """Generate and update API credentials for account"""
    try:
        new_api_key = generate_api_key()
        new_api_secret = generate_api_secret()
        
        account.api_key = new_api_key
        account.api_secret = new_api_secret
        
        db.commit()
        db.refresh(account)
        
        return new_api_key, new_api_secret
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update API credentials: {str(e)}")


@router.get("/key", response_model=ApiKeyResponse)
async def get_api_key(
    current_user: User = Depends(get_current_user_info),
    db: Session = Depends(get_db)
):
    """
    Get the current API key and API secret for the logged-in user.
    If credentials don't exist, they will be automatically created.
    
    Returns:
        ApiKeyResponse: Contains the current API key and secret
        
    Raises:
        HTTPException: If user account is not found or credential creation fails
    """
    account = get_user_account(current_user, db)
    api_key, api_secret = ensure_api_credentials(account, db)
    
    return ApiKeyResponse(
        api_key=api_key,
        api_secret=api_secret
    )


@router.get("/generate", response_model=ApiKeyUpdateResponse)
async def update_api_key(
    current_user: User = Depends(get_current_user_info),
    db: Session = Depends(get_db)
):
    """
    Generate and set new API key and API secret for the logged-in user.
    
    The API key follows the format: 'smolminds-docprocessor-' + UUID4
    The API secret is a 128-character random string.
    
    Returns:
        ApiKeyUpdateResponse: Contains the new API key, secret, and confirmation message
        
    Raises:
        HTTPException: If user account is not found or database update fails
    """
    account = get_user_account(current_user, db)
    api_key, api_secret = update_api_credentials(account, db)
    
    return ApiKeyUpdateResponse(
        api_key=api_key,
        api_secret=api_secret,
        message="API credentials successfully generated and updated"
    )