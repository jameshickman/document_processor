"""
Account management endpoints for users to view and update their account information.
"""

import os
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from api.models.database import get_db
from api.models.accounts import Account
from api.dependencies import get_current_user_info, User
from api.util.password_security import PasswordSecurity, get_password

router = APIRouter()

# Pydantic models for request/response
class AccountInfo(BaseModel):
    id: int
    name: Optional[str]
    email: str
    active: bool
    has_password: bool

class UpdateNameRequest(BaseModel):
    name: str

class UpdatePasswordRequest(BaseModel):
    old_password: Optional[str] = None
    new_password: str

# GET /account/ - Return user information
@router.get("/", response_model=AccountInfo)
async def get_account_info(
    user: User = Depends(get_current_user_info),
    db: Session = Depends(get_db)
):
    """Get the current user's account information."""
    account = db.query(Account).filter(Account.id == user.user_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return AccountInfo(
        id=account.id,
        name=account.name,
        email=account.email,
        active=account.active,
        has_password=bool(account.password_local)
    )

# POST /account/ - Update user's name
@router.post("/")
async def update_account_name(
    request: UpdateNameRequest,
    user: User = Depends(get_current_user_info),
    db: Session = Depends(get_db)
):
    """Update the user's name."""
    account = db.query(Account).filter(Account.id == user.user_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if not request.name or not request.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    
    account.name = request.name.strip()
    db.commit()
    
    return {
        "success": True,
        "message": "Name updated successfully",
        "name": account.name
    }

# POST /account/password - Update user password
@router.post("/password")
async def update_password(
    request: UpdatePasswordRequest,
    user: User = Depends(get_current_user_info),
    db: Session = Depends(get_db)
):
    """Update the user's password."""
    account = db.query(Account).filter(Account.id == user.user_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if not request.new_password or not request.new_password.strip():
        raise HTTPException(status_code=400, detail="New password cannot be empty")
    
    password_secret = os.getenv("PASSWORD_SECRET")
    if not password_secret:
        raise HTTPException(status_code=500, detail="Password secret not configured")
    
    # If user already has a password, verify the old password
    if account.password_local:
        if not request.old_password:
            raise HTTPException(status_code=400, detail="Old password is required when changing existing password")
        
        # Get and verify old password
        current_password = get_password(db, account.email, password_secret)
        if current_password != request.old_password:
            raise HTTPException(status_code=400, detail="Old password is incorrect")
    
    # Set new password
    salt = str(uuid.uuid4())
    password_security = PasswordSecurity(password_secret, salt)
    
    account.password_local = password_security.encrypt_password(request.new_password)
    account.password_encrypted = True
    account.password_salt = salt
    
    db.commit()
    
    return {
        "success": True,
        "message": "Password updated successfully"
    }