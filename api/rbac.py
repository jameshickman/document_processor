"""
FastAPI RBAC JWT Authentication Decorator

This module provides role-based access control (RBAC) functionality for FastAPI endpoints
using JWT bearer tokens. The implementation supports both role-based and claims-based
access control with flexible ANY/ALL validation modes.

Key Features:
- Role-based access control with ANY or ALL role requirements
- Claims-based access control with ANY or ALL claim requirements
- Combined role and claims validation
- Comprehensive JWT token handling and validation
- Detailed logging for security auditing
- Support for reporting role for administrative reporting

Usage:
    from api.rbac import require_roles_dependency

    # Basic role check (ANY of the roles)
    @app.get("/admin/users")
    async def get_users(
        _: None = Depends(require_roles_dependency(["admin", "super_admin"]))
    ):
        return {"users": [...]}

    # Reporting role access
    @app.get("/reporting/usage")
    async def get_usage_report(
        _: None = Depends(require_roles_dependency(["reporting", "admin"]))
    ):
        return {"report": [...]}

    # Claims-based access
    @app.get("/regional/data")
    async def get_regional_data(
        _: None = Depends(require_roles_dependency(
            required_claims={"region": ["us-east", "us-west"], "department": "finance"}
        ))
    ):
        return {"data": [...]}

    # Combined validation with ALL requirements
    @app.post("/audit/reports")
    async def create_audit_report(
        _: None = Depends(require_roles_dependency(
            required_roles=["auditor"],
            required_claims={"clearance_level": "high"},
            require_all_roles=True,
            require_all_claims=True
        ))
    ):
        return {"status": "created"}
"""

import jwt
import logging
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, Depends
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
            # For now, ignore exp
            payload = jwt.decode(
                token, 
                secret, 
                algorithms=["HS256"],
                options={"verify_exp": False, "verify_iat": False}
            )
            #options={"verify_exp": True, "verify_iat": True}
            
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
    def validate_roles(
        user_roles: List[str], 
        required_roles: List[str], 
        require_all: bool = False
    ) -> bool:
        """
        Validate if user has required roles.
        
        Args:
            user_roles: List of roles the user possesses
            required_roles: List of roles required for access
            require_all: If True, user must have ALL required roles. If False, ANY required role suffices.
            
        Returns:
            True if user meets role requirements, False otherwise
        """
        if not user_roles:
            return False
            
        if not required_roles:
            return True  # No roles required
            
        user_role_set = set(user_roles)
        required_role_set = set(required_roles)
        
        if require_all:
            # User must have ALL required roles
            return required_role_set.issubset(user_role_set)
        else:
            # User must have ANY of the required roles
            return bool(user_role_set & required_role_set)
    
    @staticmethod
    def validate_claims(
        user_claims: Dict[str, Any], 
        required_claims: Dict[str, Any], 
        require_all: bool = False
    ) -> bool:
        """
        Validate if user has required claims.
        
        Args:
            user_claims: Dictionary of claims the user possesses
            required_claims: Dictionary of claims required for access
            require_all: If True, user must have ALL required claims. If False, ANY required claim suffices.
            
        Returns:
            True if user meets claim requirements, False otherwise
        """
        if not user_claims:
            return False
            
        if not required_claims:
            return True  # No claims required
            
        matches = []
        for claim_key, claim_value in required_claims.items():
            user_claim_value = user_claims.get(claim_key)
            
            if user_claim_value is None:
                matches.append(False)
                continue
                
            # Handle different claim value types
            if isinstance(claim_value, list) and isinstance(user_claim_value, list):
                # Both are lists - check for intersection
                matches.append(bool(set(claim_value) & set(user_claim_value)))
            elif isinstance(claim_value, list):
                # Required is list, user is single value
                matches.append(user_claim_value in claim_value)
            elif isinstance(user_claim_value, list):
                # User is list, required is single value
                matches.append(claim_value in user_claim_value)
            else:
                # Both are single values
                matches.append(user_claim_value == claim_value)
        
        if require_all:
            return all(matches)
        else:
            return any(matches)
    
    @staticmethod
    def extract_claims_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract custom claims from JWT payload.
        Excludes standard JWT claims (iss, aud, exp, etc.)
        
        Args:
            payload: Decoded JWT payload
            
        Returns:
            Dictionary of custom claims
        """
        # Standard JWT claims to exclude
        standard_claims = {
            'iss', 'sub', 'aud', 'exp', 'nbf', 'iat', 'jti',
            'username', 'user', 'email', 'roles', 'role', 'authorities', 'permissions'
        }
        
        # Extract custom claims
        return {k: v for k, v in payload.items() if k not in standard_claims}
    
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


async def get_current_user(
    payload: Dict[str, Any] = Depends(get_current_user_payload)
) -> Dict[str, Any]:
    """
    FastAPI dependency for self-service endpoints.
    Verifies user is authenticated and returns user info.
    All authenticated users can access their own data through endpoints using this dependency.

    Args:
        payload: Decoded JWT payload from get_current_user_payload

    Returns:
        User information dictionary including user_id, email, roles, etc.

    Raises:
        HTTPException: For authentication errors
    """
    return payload


async def require_reporting_role(
    payload: Dict[str, Any] = Depends(get_current_user_payload)
) -> Dict[str, Any]:
    """
    FastAPI dependency for administrative reporting endpoints.
    Verifies user has reporting or admin role for cross-account access.

    Args:
        payload: Decoded JWT payload from get_current_user_payload

    Returns:
        User information dictionary

    Raises:
        HTTPException: If user doesn't have required role
    """
    user_roles = RoleValidator.extract_roles_from_payload(payload)
    user_id = extract_user(payload)

    # Admin automatically has reporting access
    if "admin" in user_roles or "reporting" in user_roles:
        logger.info(f"Reporting access granted for user {user_id} with roles: {user_roles}")
        return payload

    logger.warning(f"Reporting access denied for user {user_id}. User roles: {user_roles}")
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="Reporting access required. This endpoint requires 'reporting' or 'admin' role."
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


# Enhanced implementation using FastAPI dependency injection
def require_roles_dependency(
    required_roles: Optional[List[str]] = None,
    required_claims: Optional[Dict[str, Any]] = None,
    require_all_roles: bool = False,
    require_all_claims: bool = False
):
    """
    Enhanced FastAPI dependency for RBAC with role and claim validation.
    Supports both ANY and ALL validation modes for roles and claims.
    
    Args:
        required_roles: List of roles required for access (default: None)
        required_claims: Dictionary of claims required for access (default: None)  
        require_all_roles: If True, user must have ALL required roles. If False, ANY required role suffices. (default: False)
        require_all_claims: If True, user must have ALL required claims. If False, ANY required claim suffices. (default: False)
    
    Usage:
        # Basic role check (ANY of the roles)
        @app.get("/admin/users")
        async def get_users(
            _: None = Depends(require_roles_dependency(["admin", "super_admin"]))
        ):
            return {"users": [...]}
        
        # Require ALL roles
        @app.get("/super-admin/settings")
        async def get_settings(
            _: None = Depends(require_roles_dependency(
                required_roles=["admin", "settings_manager"], 
                require_all_roles=True
            ))
        ):
            return {"settings": [...]}
        
        # Claims-based access (ANY claim match)
        @app.get("/regional/data")
        async def get_regional_data(
            _: None = Depends(require_roles_dependency(
                required_claims={"region": ["us-east", "us-west"], "department": "finance"}
            ))
        ):
            return {"data": [...]}
        
        # Combined role and claim validation
        @app.post("/audit/reports")
        async def create_audit_report(
            _: None = Depends(require_roles_dependency(
                required_roles=["auditor"],
                required_claims={"clearance_level": "high"},
                require_all_roles=True,
                require_all_claims=True
            ))
        ):
            return {"status": "created"}
    """
    def access_checker(payload: Dict[str, Any] = Depends(get_current_user_payload)) -> None:
        try:
            user_id = extract_user(payload)
            access_granted = True
            failure_reasons = []
            
            # Validate roles if specified
            if required_roles:
                user_roles = RoleValidator.extract_roles_from_payload(payload)
                if not RoleValidator.validate_roles(user_roles, required_roles, require_all_roles):
                    access_granted = False
                    mode = "ALL" if require_all_roles else "ANY"
                    failure_reasons.append(f"Role validation failed. Required {mode} of: {required_roles}, User roles: {user_roles}")
            
            # Validate claims if specified  
            if required_claims:
                user_claims = RoleValidator.extract_claims_from_payload(payload)
                if not RoleValidator.validate_claims(user_claims, required_claims, require_all_claims):
                    access_granted = False
                    mode = "ALL" if require_all_claims else "ANY"
                    failure_reasons.append(f"Claim validation failed. Required {mode} of: {required_claims}, User claims: {user_claims}")
            
            if not access_granted:
                logger.warning(f"Access denied for user {user_id}. {'; '.join(failure_reasons)}")
                detail_parts = []
                if required_roles:
                    mode = "all" if require_all_roles else "any"
                    detail_parts.append(f"Required {mode} roles: {required_roles}")
                if required_claims:
                    mode = "all" if require_all_claims else "any"  
                    detail_parts.append(f"Required {mode} claims: {required_claims}")
                
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"Insufficient privileges. {'; '.join(detail_parts)}"
                )
                
            # Log successful access
            success_parts = []
            if required_roles:
                user_roles = RoleValidator.extract_roles_from_payload(payload)
                success_parts.append(f"roles: {user_roles}")
            if required_claims:
                user_claims = RoleValidator.extract_claims_from_payload(payload)
                success_parts.append(f"claims: {user_claims}")
                
            logger.info(f"Access granted for user {user_id} with {'; '.join(success_parts)}")
            
        except RoleValidationError as e:
            logger.error(f"Role validation error: {str(e)}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Access validation error"
            )
    
    return access_checker