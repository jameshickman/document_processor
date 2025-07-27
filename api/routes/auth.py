"""
Implement Google Auth end-points

On successfully logging in, create JWT with the field "email", and "name" field with user's full name.

JWT secret is in the environment variable JWT_SECRET

Return a JSON data package with the key "jwt" with the JWT
"""

import os
import jwt
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api import models
from api.models.database import get_db

router = APIRouter()

# Google OAuth2 configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
JWT_SECRET = os.getenv("JWT_SECRET")

# Google OAuth2 URLs
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Pydantic models
class GoogleLoginResponse(BaseModel):
    jwt: str

class GoogleCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


def validate_google_config():
    """Validate that required Google OAuth2 configuration is present"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")
    if not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_SECRET not configured")
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET not configured")


def create_jwt_token(email: str, name: str) -> str:
    """Create JWT token with email and name claims"""
    now = datetime.now(timezone.utc)
    payload = {
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + timedelta(hours=24)  # Token expires in 24 hours
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def get_google_user_info(access_token: str) -> dict:
    """Fetch user information from Google using access token"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USER_INFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")
        return response.json()


async def exchange_code_for_token(code: str) -> dict:
    """Exchange authorization code for access token"""
    token_data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GOOGLE_REDIRECT_URI,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=token_data)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        return response.json()


async def authenticate_user_with_google(code: str, db: Session) -> GoogleLoginResponse:
    """Authenticate user with Google and return JWT token"""
    # Exchange authorization code for access token
    token_response = await exchange_code_for_token(code)
    access_token = token_response.get("access_token")
    
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to obtain access token")
    
    # Get user information from Google
    user_info = await get_google_user_info(access_token)
    
    email = user_info.get("email")
    name = user_info.get("name")
    
    if not email or not name:
        raise HTTPException(status_code=400, detail="Failed to get user email or name from Google")
    
    # Check if account exists and is active
    account = db.query(models.Account).filter(models.Account.email == email).first()
    
    if not account:
        raise HTTPException(
            status_code=404, 
            detail="Account not found. Please contact administrator to create your account."
        )
    
    if not account.active:
        raise HTTPException(
            status_code=403, 
            detail="Account is not active. Please contact administrator."
        )
    
    # Create JWT token
    jwt_token = create_jwt_token(email, name)
    
    return GoogleLoginResponse(jwt=jwt_token)


@router.get("/google")
async def google_login():
    """Initiate Google OAuth2 login flow"""
    validate_google_config()
    
    # Build Google OAuth2 authorization URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle Google OAuth2 callback and create JWT token"""
    validate_google_config()
    
    # Handle OAuth2 errors
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth2 error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    try:
        return await authenticate_user_with_google(code, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/google/token")
async def google_token_exchange(
    request: GoogleCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Alternative endpoint for single-page applications to exchange authorization code for JWT.
    This is useful when the frontend handles the OAuth2 flow and just needs to exchange the code.
    """
    validate_google_config()
    
    try:
        return await authenticate_user_with_google(request.code, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/google_client_id")
async def google_client_id():
    """
    Fetch the Google Client ID for Oauth2 authentication.
    """
    return {
        "client_id": GOOGLE_CLIENT_ID,
    }


@router.get("/health")
async def auth_health():
    """Health check endpoint to verify auth service configuration"""
    try:
        validate_google_config()
        return {
            "status": "healthy",
            "google_client_configured": bool(GOOGLE_CLIENT_ID),
            "jwt_secret_configured": bool(JWT_SECRET),
            "redirect_uri": GOOGLE_REDIRECT_URI
        }
    except HTTPException as e:
        return {
            "status": "unhealthy",
            "error": e.detail,
            "google_client_configured": bool(GOOGLE_CLIENT_ID),
            "jwt_secret_configured": bool(JWT_SECRET),
            "redirect_uri": GOOGLE_REDIRECT_URI
        }