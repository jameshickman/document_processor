"""
FastAPI RBAC JWT Authentication Decorator

This module provides role-based access control (RBAC) functionality for FastAPI endpoints
using JWT bearer tokens. The implementation follows the principle of separation of concerns
by splitting JWT handling, role validation, and the decorator logic into distinct components.

Usage:
    from api.rbac import require_roles
    
    @app.get("/admin/users")
    @require_roles(["admin", "super_admin"])
    async def get_users():
        return {"users": [...]}
        
    @app.post("/moderator/content")
    @require_roles(["moderator", "admin"])
    async def moderate_content():
        return {"status": "moderated"}
"""

import jwt
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from functools import wraps

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.status import (
    HTTP_401_UNAUTHORIZED, 
    HTTP_403_FORBIDDEN, 
    HTTP_500_INTERNAL_SERVER_ERROR
)

# Import configuration
try:
    from config_loader import get_jwt_secret
except ImportError:
    # Fallback for standalone usage
    def get_jwt_secret():
        import os
        secret = os.environ.get('JWT_SECRET')
        if not secret:
            raise ValueError("JWT_SECRET environment variable not set")
        return secret

# JWT secret is now loaded from configuration instead of global variable

# Configure logging
logger = logging.getLogger(__name__)

# Security scheme for extracting bearer tokens
security = HTTPBearer()


class JWTError(Exception):
    """Custom exception for JWT-related errors"""
    pass


class RoleValidationError(Exception):
    """Custom exception for role validation errors"""
    pass


def extract_user(payload: dict[str, Any]) -> str:
    user_fields = ['username', 'user', 'sub', 'email']
    for field in user_fields:
        if field in payload:
            return payload[field]
    return 'anonymous'


class JWTHandler:
    """
    Handles JWT token operations including decoding and validation.
    Separated into its own class to follow Single Responsibility Principle.
    """
    
    @staticmethod
    def decode_token(token: str, secret: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: The JWT token string
            secret: The secret key for JWT verification
            
        Returns:
            Decoded JWT payload as dictionary
            
        Raises:
            JWTError: If token is invalid, expired, or malformed
        """
        try:
            payload = jwt.decode(
                token, 
                secret, 
                algorithms=["HS256"],
                options={"verify_exp": True, "verify_iat": True}
            )
            
            # Additional validation
            if not payload:
                raise JWTError("Empty payload in JWT token")
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            raise JWTError("Token has expired")
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            raise JWTError("Invalid token")
            
        except Exception as e:
            logger.error(f"Unexpected error decoding JWT: {str(e)}")
            raise JWTError("Token processing error")


class RoleValidator:
    """
    Handles role validation logic.
    Separated to allow for easy extension of role validation rules.
    """
    
    @staticmethod
    def validate_roles(user_roles: List[str], required_roles: List[str]) -> bool:
        """
        Validate if user has any of the required roles.
        
        Args:
            user_roles: List of roles the user possesses
            required_roles: List of roles required for access
            
        Returns:
            True if user has at least one required role, False otherwise
        """
        if not user_roles:
            return False
            
        if not required_roles:
            return True  # No roles required
            
        # Check if user has any of the required roles
        return bool(set(user_roles) & set(required_roles))
    
    @staticmethod
    def extract_roles_from_payload(payload: Dict[str, Any]) -> List[str]:
        """
        Extract roles from JWT payload.
        Handles various common JWT role claim formats.
        
        Args:
            payload: Decoded JWT payload
            
        Returns:
            List of role strings
            
        Raises:
            RoleValidationError: If roles cannot be extracted
        """
        # Try different common role claim names
        role_claims = ['roles', 'role', 'authorities', 'permissions']
        
        for claim in role_claims:
            if claim in payload:
                roles = payload[claim]
                
                # Handle different role formats
                if isinstance(roles, str):
                    # Single role as string or comma-separated
                    return [r.strip() for r in roles.split(',') if r.strip()]
                elif isinstance(roles, list):
                    # List of roles
                    return [str(role).strip() for role in roles if role]
                    
        # If no role claims found, return empty list
        logger.warning("No role claims found in JWT payload")
        return []


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to extract and validate JWT from request.
    
    Args:
        credentials: HTTP Authorization credentials from FastAPI security
        
    Returns:
        Decoded JWT payload
        
    Raises:
        HTTPException: For authentication errors
    """
    try:
        jwt_secret = get_jwt_secret()
    except ValueError as e:
        logger.error(f"JWT secret configuration error: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not properly configured"
        )
    
    try:
        payload = JWTHandler.decode_token(credentials.credentials, jwt_secret)
        
        # Log successful authentication (without sensitive data)
        user_id = extract_user(payload)
        logger.info(f"Successfully authenticated user: {user_id}")
        
        return payload
        
    except JWTError as e:
        logger.warning(f"JWT authentication failed: {str(e)}")
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


# Legacy function for backward compatibility - now uses config loader
def configure_jwt_secret(secret: str) -> None:
    """
    Legacy function for backward compatibility.
    JWT secret is now loaded from configuration automatically.
    
    Args:
        secret: JWT secret key (ignored - loaded from config)
    """
    logger.info("JWT secret configuration called - using config loader instead")


# Alternative implementation using FastAPI dependency injection
def require_roles_dependency(required_roles: List[str]):
    """
    Alternative implementation using FastAPI's dependency system.
    This approach is more explicit and follows FastAPI conventions better.
    
    Usage:
        @app.get("/admin/users")
        async def get_users(
            user_payload: dict = Depends(get_current_user_payload),
            _: None = Depends(require_roles_dependency(["admin"]))
        ):
            return {"users": [...]}
    """
    def role_checker(payload: Dict[str, Any] = Depends(get_current_user_payload)) -> None:
        try:
            user_roles = RoleValidator.extract_roles_from_payload(payload)
            
            if not RoleValidator.validate_roles(user_roles, required_roles):
                user_id = extract_user(payload)
                logger.warning(
                    f"Access denied for user {user_id}. "
                    f"Required roles: {required_roles}, User roles: {user_roles}"
                )
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"Insufficient privileges. Required roles: {required_roles}"
                )
                
            user_id = extract_user(payload)
            logger.info(f"Access granted for user {user_id} with roles: {user_roles}")
            
        except RoleValidationError as e:
            logger.error(f"Role validation error: {str(e)}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role validation error"
            )
    
    return role_checker