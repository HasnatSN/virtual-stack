from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Security, status, Request
from fastapi.security import APIKeyHeader, APIKeyQuery, OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.config import settings
from virtualstack.core.exceptions import http_authentication_error
from virtualstack.core.permissions import Permission
from virtualstack.db.session import get_db
from virtualstack.models.iam import User, Role, Permission as PermissionModel
from virtualstack.schemas.iam.auth import TokenPayload
from virtualstack.services.iam import user_service
from virtualstack.services.iam.api_key import api_key_service
from virtualstack.models.iam.user_tenant_role import user_tenant_roles_table
from virtualstack.models.iam.role_permissions import role_permissions_table
from sqlalchemy import select, distinct, exists
import logging

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token", auto_error=False
)

# API Key authentication schemes
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)

# TODO: Decide on final Tenant Header name and document it
TENANT_ID_HEADER = "X-Tenant-ID"

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
        raise http_authentication_error(detail="Invalid or expired API Key")

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


# TODO: Add tests for API Key validation scenarios
# TODO: Consider rate limiting for API Key validation
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
        raise http_authentication_error(detail="Invalid or expired API Key")

    # Extract user from the result tuple (api_key_obj, user)
    _, user = result
    return user


# TODO: Document the expected header for tenant ID (e.g., X-Tenant-ID)
# TODO: Add tests for various tenant ID header scenarios (missing, invalid format)
def get_tenant_id_from_header(request: Request) -> Optional[UUID]:
    """Dependency to extract and validate tenant_id from a request header."""
    tenant_id_str = request.headers.get(TENANT_ID_HEADER)
    if not tenant_id_str:
        # If header is missing, we cannot determine tenant context
        logger.warning(f"Tenant context header '{TENANT_ID_HEADER}' missing.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing tenant context header: {TENANT_ID_HEADER}"
        )
    try:
        tenant_id = UUID(tenant_id_str)
        return tenant_id
    except ValueError:
        # Handle invalid UUID format in header
        logger.warning(f"Invalid UUID format in {TENANT_ID_HEADER} header: {tenant_id_str}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Tenant ID format in header '{TENANT_ID_HEADER}'."
        )


# TODO: Add tests for tenant existence check with header dependency
async def check_tenant_exists(db: AsyncSession, tenant_id: UUID) -> UUID:
    """Helper function (not a dependency itself) to check if a tenant exists."""
    # Import tenant_service locally to avoid circular dependencies at module level
    from virtualstack.services.iam import tenant_service
    tenant = await tenant_service.get(db, record_id=tenant_id)
    if not tenant:
        logger.warning(f"Tenant existence check failed: Tenant {tenant_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found."
        )
    return tenant_id # Return the validated tenant_id


# TODO: Ensure frontend sends the correct Tenant ID header
# TODO: Add tests for this consolidated dependency
async def get_validated_tenant_id(
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_tenant_id_from_header)
) -> UUID:
    """Consolidated dependency: gets tenant ID from header and validates its existence."""
    return await check_tenant_exists(db=db, tenant_id=tenant_id)


# TODO: Add tests for permission checks using header-based tenant ID
# TODO: Add require_any_permission and require_all_permissions variants using header
def require_permission(permission: Permission):
    """Dependency factory that requires a specific permission within the tenant context
    derived from the request header (e.g., X-Tenant-ID).
    """

    async def check_permission(
        current_user: User = Depends(get_current_active_user),
        # Depend on get_validated_tenant_id to ensure tenant_id is valid and tenant exists
        tenant_id: UUID = Depends(get_validated_tenant_id),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        """Checks if the current user has the required permission within the tenant context."""
        # Superusers have all permissions
        if current_user.is_superuser:
            return current_user

        # --- Check User Tenant Membership & Permission ---
        # Combine checks for efficiency: Find if user has *any* role in the tenant
        # that grants the required permission.
        has_permission_stmt = (
            select(exists())
            .select_from(user_tenant_roles_table)
            .join(role_permissions_table, user_tenant_roles_table.c.role_id == role_permissions_table.c.role_id)
            .join(PermissionModel, role_permissions_table.c.permission_id == PermissionModel.id)
            .where(
                user_tenant_roles_table.c.user_id == current_user.id,
                user_tenant_roles_table.c.tenant_id == tenant_id,
                PermissionModel.code == permission.value # Compare with permission enum's value (string code)
            )
        )

        has_perm = await db.scalar(has_permission_stmt)

        if not has_perm:
            logger.warning(
                f"Permission denied: User {current_user.id} lacks permission '{permission.value}' in Tenant {tenant_id} (derived from header)."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action in this tenant.",
            )

        # If permission check passes, return the user object
        return current_user

    return check_permission


# --- Resource-Specific Permission Checks (Examples - Adapt as needed) ---

# Example: Check if user can manage a specific Role (is it custom and in their tenant?)
# async def require_role_management_permission(
#     role_id: UUID,
#     tenant_id: UUID = Depends(check_tenant_exists),
#     current_user: User = Depends(get_current_active_user),
#     db: AsyncSession = Depends(get_db),
# ) -> Role:
#     """Dependency to check if user can manage a specific role.
#     Ensures the role exists, is custom (not system), and belongs to the current tenant context.
#     Also implicitly requires ROLE_UPDATE or ROLE_DELETE permission via other dependencies.
#     """
#     role = await role_service.get(db, record_id=role_id)
#     if not role:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
#     if role.is_system_role:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot manage system roles.")
#     if role.tenant_id != tenant_id:
#         # This check might be redundant if the caller route already enforces tenant context
#         # but it provides an extra layer of security.
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role does not belong to this tenant.")
#     return role


# TODO: Define similar dependencies for other resources like Invitations, API Keys, etc.
# ensuring checks for tenant ownership and necessary permissions are performed.

# TODO: Refactor permission checks to be more granular and potentially cache results
# for complex scenarios or performance optimization if needed later.
