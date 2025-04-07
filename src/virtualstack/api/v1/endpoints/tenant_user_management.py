from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api import deps
from virtualstack.api.deps import get_tenant_from_path
from virtualstack.models.iam.tenant import Tenant
from virtualstack.schemas.iam.role import RoleAssign
from virtualstack.schemas.iam.user import User as UserSchema, UserListResponse
from virtualstack.services.iam import user_service, tenant_service, role_service
import logging

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/",
    response_model=UserListResponse,
    dependencies=[Depends(deps.require_permission("tenant:view_users"))]
)
async def list_users_in_tenant(
    *,
    db: AsyncSession = Depends(deps.get_db),
    tenant: Tenant = Depends(get_tenant_from_path),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for user email/name")
) -> UserListResponse:
    """Retrieve users within the specified tenant with pagination and search."""
    users, total_count = await user_service.get_multi_by_tenant_paginated(
        db,
        tenant_id=tenant.id,
        skip=(page - 1) * limit,
        limit=limit,
        search=search
    )
    return UserListResponse(
        items=users,
        total=total_count,
        page=page,
        limit=limit,
    )

@router.get(
    "/{user_id}",
    response_model=UserSchema,
    dependencies=[Depends(deps.require_permission("tenant:view_users"))]
)
async def get_tenant_user(
    *,
    tenant: Tenant = Depends(get_tenant_from_path),
    user_id: UUID = Path(...),
    db: AsyncSession = Depends(deps.get_db),
) -> UserSchema:
    """Get details for a specific user within a tenant."""
    user = await user_service.get_by_id_and_tenant(db, record_id=user_id, tenant_id=tenant.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found within this tenant")

    return user

@router.post(
    "/{user_id}/roles",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def assign_role_to_user(
    *,
    tenant: Tenant = Depends(get_tenant_from_path),
    user_id: UUID = Path(...),
    role_assignment: RoleAssign,
    db: AsyncSession = Depends(deps.get_db),
    requesting_user: UserSchema = Depends(deps.require_permission("role:assign_users")),
) -> None:
    """Assign a role to a user within a specific tenant."""
    try:
        assigned = await user_service.assign_role_to_user_in_tenant(
            db=db,
            user_id=user_id,
            role_id=role_assignment.role_id,
            tenant_id=tenant.id,
        )
        if not assigned:
            logger.info(f"Role {role_assignment.role_id} already assigned to user {user_id} in tenant {tenant.id}")
        else:
            logger.info(f"Role {role_assignment.role_id} assigned to user {user_id} in tenant {tenant.id}")
    except deps.NotFoundError as e:
        logger.warning(f"Role assignment failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except deps.ValidationError as e:
        logger.warning(f"Role assignment validation error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to assign role {role_assignment.role_id} to user {user_id} in tenant {tenant.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during role assignment."
        )

    return None

@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_role_from_user(
    *,
    tenant: Tenant = Depends(get_tenant_from_path),
    user_id: UUID = Path(...),
    role_id: UUID = Path(...),
    db: AsyncSession = Depends(deps.get_db),
    requesting_user: UserSchema = Depends(deps.require_permission("role:assign_users")),
) -> None:
    """Remove a specific role assignment from a user within a tenant."""
    deleted_count = await user_service.remove_role_from_user_in_tenant(
        db=db,
        user_id=user_id,
        role_id=role_id,
        tenant_id=tenant.id,
    )

    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} assignment not found for user {user_id} in tenant {tenant.id}"
        )

    logger.info(f"Successfully removed role {role_id} from user {user_id} in tenant {tenant.id}")
    return None