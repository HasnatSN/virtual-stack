from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery, OAuth2PasswordBearer
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.config import settings
from virtualstack.core.exceptions import http_authentication_error
from virtualstack.core.permissions import Permission
from virtualstack.db.session import get_db
from virtualstack.models.iam import User
from virtualstack.schemas.iam.auth import TokenPayload
from virtualstack.services.iam import user_service
from virtualstack.services.iam.api_key import api_key_service


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token", auto_error=False
)

# API Key authentication schemes
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_current_user_from_token(
    db: AsyncSession = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[User]:
    """Decode JWT token and retrieve user from database."""
    if not token:
        return None

    try:
        payload_dict = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        # Validate payload structure using Pydantic model
        payload = TokenPayload.model_validate(payload_dict)
        user_id_str = payload.sub
        if user_id_str is None:
            raise http_authentication_error(detail="Invalid token payload: Subject missing")

        user_id = UUID(user_id_str)  # Convert sub to UUID

        # Get user from database using record_id
        user = await user_service.get(db, record_id=user_id)
        if not user:
            raise http_authentication_error(detail="User not found for token")

        return user
    except jwt.ExpiredSignatureError as e:
        raise http_authentication_error(detail="Token has expired") from e
    except jwt.PyJWTError as e:
        raise http_authentication_error(detail="Could not validate token") from e
    except ValueError as e:  # Handle invalid UUID format in token subject
        raise http_authentication_error(detail="Invalid user ID format in token") from e


async def get_current_user_from_api_key(
    db: AsyncSession = Depends(get_db),
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
) -> Optional[User]:
    """Get and validate API key from header or query parameter.
    Returns the user associated with the API key if valid.
    """
    api_key = api_key_header or api_key_query
    if not api_key:
        return None

    # Validate the API key using the service
    result = await api_key_service.validate_api_key(db=db, api_key=api_key)

    if not result:
        return None  # Service handles logging/errors internally for invalid keys

    # Extract user from the result tuple (api_key_obj, user)
    _, user = result
    return user


async def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key),
) -> User:
    """Get current user from either JWT token or API key.
    Raises HTTPException if neither authentication method provides a valid user.
    """
    user = token_user or api_key_user
    if not user:
        raise http_authentication_error(detail="Not authenticated")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


# Extract current tenant ID from request context (Placeholder - needs tenant context implementation)
async def get_current_tenant_id(
    # Depends on how tenant context is established (e.g., from token, header, user profile)
    # current_user: User = Depends(get_current_active_user),
) -> Optional[UUID]:
    """Get the current tenant ID from the request context (Placeholder).

    For API keys, this *could* be derived if the key is tenant-scoped.
    For user tokens, this needs a mechanism like a selected tenant header or user default.

    Returns None if no specific tenant context is identified.
    """
    # TODO: Implement actual tenant context logic
    # This might involve looking at custom headers, claims in JWT,
    # or properties associated with the authenticated user or API key.
    # For now, returning None simulates a global context.
    return None


# Permission checking dependencies (Needs actual implementation)
def require_permission(permission: Permission):
    """Dependency factory that requires a specific permission (currently mocked)."""

    async def check_permission(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        # Superusers have all permissions
        if current_user.is_superuser:
            return current_user

        # --- Mock Implementation Start ---
        # For now, just check if the user is a superuser or allow common reads
        if permission == Permission.TENANT_CREATE and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions: {permission} required",
            )

        common_read_permissions = [
            Permission.USER_READ,
            Permission.TENANT_READ,
            Permission.API_KEY_READ,
            Permission.ROLE_READ,
            Permission.INVITATION_READ,
        ]
        if permission in common_read_permissions:
            return current_user
        # Allow self-management of API keys
        if permission in [
            Permission.API_KEY_CREATE,
            Permission.API_KEY_UPDATE,
            Permission.API_KEY_DELETE,
        ]:
            return current_user

        # Deny other permissions for non-superusers in mock implementation
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied (mock implementation): requires {permission}",
        )
        # --- Mock Implementation End ---

        # return current_user # Return user if permission check passes

    return check_permission


def require_any_permission(permissions: list[Permission]):
    """Dependency factory that requires any of the specified permissions."""

    async def check_permissions(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        # Superusers have all permissions
        if current_user.is_superuser:
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
            detail=f"Not enough permissions: require any of {list(permissions)}",
        )

    return check_permissions


def require_all_permissions(permissions: list[Permission]):
    """Dependency factory that requires all of the specified permissions."""

    async def check_permissions(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        # Superusers have all permissions
        if current_user.is_superuser:
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
            detail=f"Not enough permissions: require all of {list(permissions)}",
        )

    return check_permissions
