from typing import Dict, Optional, Union, List, Callable
from datetime import datetime, timedelta
import jwt
from pydantic import UUID4
from functools import wraps

from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader, APIKeyQuery
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.config import settings
from virtualstack.core.exceptions import http_authentication_error
from virtualstack.core.permissions import Permission, get_user_permissions, has_permission, has_any_permission, has_all_permissions
from virtualstack.db.session import get_db
from virtualstack.services.iam.api_key import api_key_service
from virtualstack.models.iam import User
from virtualstack.models.iam.api_key import APIKey

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)

# API Key authentication schemes
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[Dict]:
    """
    Get current user based on JWT token.
    
    Note: This is a simplified implementation for demo purposes.
    Will be expanded when the User model is fully integrated.
    """
    if not token:
        return None
        
    # For demo purposes, return a mock user
    return {"id": "123e4567-e89b-12d3-a456-426614174000", "email": "admin@example.com", "is_superuser": True}
    
    # Original implementation to be used later:
    # try:
    #     payload = jwt.decode(
    #         token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    #     )
    #     user_id: UUID4 = payload.get("sub")
    #     if user_id is None:
    #         raise http_authentication_error()
    #     
    #     # Get user from database
    #     user = await user_service.get_by_id(user_id)
    #     if user is None:
    #         raise http_authentication_error()
    #         
    #     return user
    # except jwt.PyJWTError:
    #     raise http_authentication_error()


async def get_api_key(
    db: AsyncSession = Depends(get_db),
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
) -> Optional[Dict]:
    """
    Get and validate API key from header or query parameter.
    Returns the user associated with the API key if valid.
    """
    api_key = api_key_header or api_key_query
    if not api_key:
        return None
    
    # Validate the API key
    result = await api_key_service.validate_api_key(db=db, api_key=api_key)
    
    if not result:
        return None
        
    # Extract API key and user
    api_key_obj, user = result
    
    # For now, we'll convert the User model to a dict for compatibility
    return {
        "id": str(user.id),
        "email": user.email,
        "is_superuser": user.is_superuser,
        "is_active": user.is_active,
        "api_key_id": str(api_key_obj.id),
        "tenant_id": str(api_key_obj.tenant_id) if api_key_obj.tenant_id else None,
    }


async def get_current_user_from_token_or_api_key(
    db: AsyncSession = Depends(get_db),
    token_user: Optional[Dict] = Depends(get_current_user),
    api_key_user: Optional[Dict] = Depends(get_api_key),
) -> Dict:
    """
    Get current user from either JWT token or API key.
    
    This allows endpoints to be authenticated with either method.
    """
    user = token_user or api_key_user
    if not user:
        raise http_authentication_error(detail="Not authenticated")
    return user


async def get_current_active_user(
    current_user: Dict = Depends(get_current_user_from_token_or_api_key),
) -> Dict:
    """
    Get current active user.
    """
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


async def get_current_superuser(
    current_user: Dict = Depends(get_current_active_user),
) -> Dict:
    """
    Get current superuser.
    """
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


# Extract current tenant ID from request context
async def get_current_tenant_id(
    current_user: Dict = Depends(get_current_active_user),
) -> Optional[str]:
    """
    Get the current tenant ID from the user context.
    
    For API keys, this will be the tenant_id from the API key (if present).
    For user tokens, we would normally get this from a tenant selection or default tenant.
    
    Returns None for global context (no tenant specified).
    """
    return current_user.get("tenant_id")


# Permission checking dependencies
def require_permission(permission: Permission):
    """
    Dependency factory that requires a specific permission.
    
    Usage:
        @router.get("/protected")
        async def protected_route(
            current_user: Dict = Depends(require_permission(Permission.USER_READ))
        ):
            ...
    """
    async def check_permission(
        db = Depends(get_db),
        current_user: Dict = Depends(get_current_active_user),
        tenant_id: Optional[str] = Depends(get_current_tenant_id),
    ) -> Dict:
        # Superusers have all permissions
        if current_user.get("is_superuser"):
            return current_user
            
        # For now, just check if the user is a superuser
        # In a real implementation, we would check actual permissions
        if permission == Permission.TENANT_CREATE:
            # Only superusers can create tenants
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions: {permission} required",
            )
            
        # For demonstration, assume regular users have common permissions
        if permission in [
            Permission.USER_READ, 
            Permission.TENANT_READ, 
            Permission.API_KEY_READ,
            Permission.API_KEY_CREATE,
            Permission.API_KEY_UPDATE,
            Permission.API_KEY_DELETE,
        ]:
            return current_user
            
        # For unhandled permissions, deny access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions: {permission} required",
        )
        
    return check_permission


def require_any_permission(permissions: List[Permission]):
    """
    Dependency factory that requires any of the specified permissions.
    """
    async def check_permissions(
        db = Depends(get_db),
        current_user: Dict = Depends(get_current_active_user),
        tenant_id: Optional[str] = Depends(get_current_tenant_id),
    ) -> Dict:
        # Superusers have all permissions
        if current_user.get("is_superuser"):
            return current_user
            
        # For now, just simulate permission checking
        # In a real implementation, we would check actual permissions
        
        # For demonstration, assume regular users have common permissions
        common_permissions = [
            Permission.USER_READ, 
            Permission.TENANT_READ, 
            Permission.API_KEY_READ,
            Permission.API_KEY_CREATE,
            Permission.API_KEY_UPDATE,
            Permission.API_KEY_DELETE,
        ]
        
        if any(p in common_permissions for p in permissions):
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions: require any of {[p for p in permissions]}",
        )
        
    return check_permissions


def require_all_permissions(permissions: List[Permission]):
    """
    Dependency factory that requires all of the specified permissions.
    """
    async def check_permissions(
        db = Depends(get_db),
        current_user: Dict = Depends(get_current_active_user),
        tenant_id: Optional[str] = Depends(get_current_tenant_id),
    ) -> Dict:
        # Superusers have all permissions
        if current_user.get("is_superuser"):
            return current_user
            
        # For now, just simulate permission checking
        # In a real implementation, we would check actual permissions
        
        # For demonstration, assume regular users have common permissions
        common_permissions = [
            Permission.USER_READ, 
            Permission.TENANT_READ, 
            Permission.API_KEY_READ,
            Permission.API_KEY_CREATE,
            Permission.API_KEY_UPDATE,
            Permission.API_KEY_DELETE,
        ]
        
        if all(p in common_permissions for p in permissions):
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions: require all of {[p for p in permissions]}",
        )
        
    return check_permissions
