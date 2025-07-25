from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from api import models
from api.models.database import get_db
from api.models.accounts import Account

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from api.rbac import get_current_user_payload


# Export all public functions and classes
__all__ = [
    'AccountSchema', 'User', 'get_current_user_info'
]


# Pydantic schemas
class AccountSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: Optional[str] = None
    email: Optional[str] = None
    time_created: Optional[datetime] = None
    active: bool = True
    grandfathered: bool = False
    api_key: Optional[str] = None


class User(BaseModel):
    user_id: int
    username: str
    email: str
    roles: list = Field(default_factory=list)
    account: Optional[AccountSchema] = None


async def get_current_user_info(
        payload: dict = Depends(get_current_user_payload),
        db: Session = Depends(get_db)
) -> User:
    """Get current user from RBAC JWT payload"""

    username = payload.get("username") or payload.get("user") or payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username not found in token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    roles = payload.get("roles", [])

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not found in token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_account = db.query(models.Account).filter_by(email=email).first()

    if not user_account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found in database",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user_account.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not active",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return User(
        user_id=int(user_account.id),
        username=username,
        roles=roles,
        email=email,
        account=AccountSchema.model_validate(user_account) if user_account else None)
