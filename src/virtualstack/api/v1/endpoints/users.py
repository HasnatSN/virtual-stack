from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import (
    get_current_user,
    get_tenant_from_path,
    require_permission,
    get_current_active_tenant,
    require_permission_in_active_tenant,
    get_db,
)
from virtualstack.core.exceptions import http_not_found_error, http_validation_error
from virtualstack.models.iam.user import User
from virtualstack.models.iam.tenant import Tenant
from virtualstack.schemas.iam.user import User as UserSchema
from virtualstack.schemas.iam.user import UserCreate, UserUpdate, UserListResponse, UserStatusUpdate
from virtualstack.services.iam import user_service
from virtualstack.core.permissions import Permission
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List Users in Active Tenant",
    description="Retrieves users within the currently active tenant (specified by X-Tenant-ID header) with pagination and search.",
    dependencies=[Depends(require_permission_in_active_tenant(Permission.USER_READ))]
)
async def list_users_in_active_tenant(
    *,
    db: AsyncSession = Depends(get_db),
    active_tenant: Tenant = Depends(get_current_active_tenant),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for user email/name")
) -> UserListResponse:
    """Retrieve users within the user's active tenant."""
    logger.info(f"Listing users for tenant {active_tenant.id} (active) with page={page}, limit={limit}, search='{search}'")
    users, total_count = await user_service.get_multi_by_tenant_paginated(
        db,
        tenant_id=active_tenant.id,
        skip=(page - 1) * limit,
        limit=limit,
        search=search
    )
    logger.debug(f"Found {total_count} users for tenant {active_tenant.id} (active). Returning {len(users)} users for page {page}.")
    return UserListResponse(
        items=users,
        total=total_count,
        page=page,
        limit=limit,
    )


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(*, current_user: User = Depends(get_current_user)) -> UserSchema:
    """Get current authenticated user information."""
    return current_user


@router.put("/me", response_model=UserSchema)
async def update_current_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update current authenticated user information."""
    return await user_service.update(db, db_obj=current_user, obj_in=user_in)


@router.patch(
    "/{user_id}",
    response_model=UserSchema,
    summary="Update User Status in Active Tenant",
    description="Updates the active status of a specific user within the currently active tenant.",
    dependencies=[Depends(require_permission_in_active_tenant(Permission.USER_UPDATE))]
)
async def update_user_status_in_active_tenant(
    *,
    user_id: UUID = Path(..., description="The ID of the user to update"),
    user_in: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    active_tenant: Tenant = Depends(get_current_active_tenant),
) -> UserSchema:
    """Update the is_active status of a user within the active tenant."""
    logger.info(f"Attempting to update status for user {user_id} in active tenant {active_tenant.id}")

    # 1. Verify the user exists within the active tenant
    db_user = await user_service.get_by_id_and_tenant(db, record_id=user_id, tenant_id=active_tenant.id)
    if not db_user:
        logger.warning(f"User status update failed: User {user_id} not found in active tenant {active_tenant.id}")
        raise http_not_found_error(detail=f"User {user_id} not found within this tenant context.")

    # TODO: Add logic to prevent deactivating the last active admin in a tenant?
    # This would require checking roles and other active admins.
    if not user_in.is_active:
        logger.warning(f"Deactivating user {user_id} in tenant {active_tenant.id}. Consider adding last admin checks.")

    # 2. Update the user using the generic service update method
    try:
        updated_user = await user_service.update(db, db_obj=db_user, obj_in=user_in.model_dump())
        logger.info(f"Successfully updated status for user {user_id} in active tenant {active_tenant.id} to is_active={user_in.is_active}")
        return updated_user
    except Exception as e:
        # Log the error and return a generic 500
        logger.error(f"Error updating status for user {user_id} in active tenant {active_tenant.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while updating the user status.")


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove User from Active Tenant",
    description="Removes a user's association from the currently active tenant. This does not delete the global user record.",
    dependencies=[Depends(require_permission_in_active_tenant(Permission.USER_DELETE))]
)
async def remove_user_from_active_tenant(
    *,
    user_id: UUID = Path(..., description="The ID of the user to remove from the tenant"),
    db: AsyncSession = Depends(get_db),
    active_tenant: Tenant = Depends(get_current_active_tenant),
) -> None:
    """Remove a user's association from the active tenant."""
    logger.info(f"Attempting to remove user {user_id} from active tenant {active_tenant.id}")

    # 1. Verify the user *currently* exists within the active tenant before trying to remove
    db_user = await user_service.get_by_id_and_tenant(db, record_id=user_id, tenant_id=active_tenant.id)
    if not db_user:
        logger.warning(f"User removal failed: User {user_id} not found in active tenant {active_tenant.id}")
        # Return 204 even if not found, as the end state (user not associated) is achieved.
        # Alternatively, could return 404, but 204 is often preferred for DELETE idempotency.
        return None

    # TODO: Add check to prevent removing the last admin?

    # 2. Call the service to remove the tenant association
    try:
        deleted_count = await user_service.delete(db, record_id=user_id, tenant_id=active_tenant.id)
        # Service loggs warning if count is 0, which we already checked above, but double negative is ok.
        logger.info(f"Successfully removed user {user_id} association from active tenant {active_tenant.id}. Associations removed: {deleted_count}")
        # No explicit return needed for 204
    except Exception as e:
        # Log the error and return a generic 500
        logger.error(f"Error removing user {user_id} from active tenant {active_tenant.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while removing the user from the tenant.")

    return None # Explicitly return None for 204 status code


# General TODOs for this file:
# - Clarify if /me endpoints belong here or elsewhere.
# - Add logging to /me endpoints.
# - TODO: Add endpoints for user update (PATCH /users/{user_id}) and delete (DELETE /users/{user_id}) if needed for MVP, using active tenant context.
# - TODO: Update UserListResponse schema/service to include user roles.
