from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from api import models
from api.models.database import get_db
from api.models.accounts import Account

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field, ConfigDict
from api.rbac import get_current_user_payload
import secrets


# Initialize HTTP Basic Auth security
security = HTTPBasic()

# Export all public functions and classes
__all__ = [
    'AccountSchema', 'User', 'get_current_user_info', 'get_basic_auth'
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

    user_account = db.query(models.Account).filter(models.Account.email == email).first()

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


async def get_basic_auth(
        credentials: HTTPBasicCredentials = Depends(security),
        db: Session = Depends(get_db)
) -> User:
    """HTTP Basic Auth dependency that validates credentials against the database
    
    Usage example:
    @app.post("/protected-endpoint")
    async def protected_route(user: User = Depends(get_basic_auth)):
        return {"message": f"Hello {user.username}"}
    """
    
    user_account = db.query(models.Account).filter(models.Account.api_key == credentials.username).first()
    
    if not user_account or not user_account.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"}
        )

    if not user_account.api_key or not user_account.api_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No API credentials set",
            headers={"WWW-Authenticate": "Basic"}
        )
    
    if not user_account.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key not configured for account",
            headers={"WWW-Authenticate": "Basic"}
        )
    
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        user_account.api_secret.encode("utf8")
    )
    
    if not is_correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"}
        )
    
    return User(
        user_id=int(user_account.id),
        username=user_account.email or credentials.username,
        roles=[],
        email=user_account.email or credentials.username,
        account=AccountSchema.model_validate(user_account)
    )
