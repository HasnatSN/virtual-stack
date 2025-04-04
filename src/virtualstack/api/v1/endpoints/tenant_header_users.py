from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import get_db, get_current_user, get_current_active_user, get_validated_tenant_id, require_permission
from virtualstack.core.exceptions import http_not_found_error, http_validation_error
from virtualstack.core.permissions import Permission
from virtualstack.db.session import get_db
from virtualstack.models.iam.user import User
from virtualstack.schemas.iam.user import User as UserSchema
from virtualstack.schemas.iam.user import UserCreate, UserUpdate
from virtualstack.services.iam import user_service


router = APIRouter()


# TODO: Create proper pagination response model
# TODO: Add count of total users
@router.get("/", response_model=List[Dict[str, Any]])
async def get_users(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = Query(None),
    _: User = Depends(require_permission(Permission.USER_READ)),
) -> Any:
    """Retrieve users within the current tenant with their assigned roles.
    Supports pagination and optional search by name or email.
    """
    users_with_roles = await user_service.get_users_by_tenant_with_roles(
        db, tenant_id=tenant_id, skip=skip, limit=limit, search=search
    )
    return users_with_roles


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    *, 
    current_user: User = Depends(get_current_active_user)
) -> UserSchema:
    """Get current user information."""
    return current_user


@router.patch("/{user_id}", response_model=UserSchema)
async def update_user(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    user_id: UUID = Path(...),
    user_in: UserUpdate,
    _: User = Depends(require_permission(Permission.USER_UPDATE)),
) -> Any:
    """Update user information (activation status)."""
    # First verify the user exists and is in the tenant
    is_in_tenant = await user_service.is_user_in_tenant(db, user_id=user_id, tenant_id=tenant_id)
    if not is_in_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this tenant"
        )
    
    # Get the user to update
    user = await user_service.get(db, record_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update the user (only allowed fields like is_active)
    update_data = user_in.model_dump(exclude_unset=True)
    allowed_fields = {"is_active"}
    filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    # If no allowed fields were provided, return early
    if not filtered_data:
        return user
        
    # Create a new UserUpdate with only the allowed fields
    filtered_update = UserUpdate(**filtered_data)
    updated_user = await user_service.update(db, db_obj=user, obj_in=filtered_update)
    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_tenant(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    user_id: UUID = Path(...),
    _: User = Depends(require_permission(Permission.USER_DELETE)),
) -> None:
    """Remove a user from the tenant (removes all roles in the tenant).
    This doesn't delete the user from the system, just removes them from this tenant.
    """
    # First verify the user exists and is in the tenant
    is_in_tenant = await user_service.is_user_in_tenant(db, user_id=user_id, tenant_id=tenant_id)
    if not is_in_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in this tenant"
        )
        
    # TODO: Implement remove_user_from_tenant in the user service
    # This would remove all user-tenant-role associations for this user in this tenant
    # For now, we'll just return a not implemented error
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Removing a user from a tenant is not yet implemented"
    ) 