from uuid import UUID
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import (
    get_db,
    get_current_active_user,
    get_tenant_from_path,
    require_permission,
    get_current_active_tenant,
    require_permission_in_active_tenant,
)
from virtualstack.core.permissions import Permission
from virtualstack.schemas.iam import (
    Role,
    RoleCreate,
    RoleUpdate,
    RoleList,
    RoleDetail,
    RoleUserAssignmentInput,
    RoleUserAssignmentOutput
)
from virtualstack.schemas.iam.permission import Permission as PermissionSchema
from virtualstack.services.iam import permission_service, role_service
from virtualstack.models.iam.user import User
from virtualstack.models.iam.tenant import Tenant

router = APIRouter()


@router.get(
    "/",
    response_model=List[RoleList],
    summary="List Roles in Active Tenant",
    description="Lists roles (system & custom) available within the active tenant, including user counts."
)
async def list_roles_in_active_tenant(
    *,
    active_tenant: Tenant = Depends(get_current_active_tenant),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission_in_active_tenant(Permission.ROLE_READ)),
):
    """List roles available within the user's active tenant."""
    logger.info(f"Listing roles for active tenant {active_tenant.id} with skip={skip}, limit={limit}")
    roles_with_count = await role_service.get_multi_by_tenant_with_user_count(
        db, tenant_id=active_tenant.id, skip=skip, limit=limit
    )
    logger.debug(f"Found {len(roles_with_count)} roles for active tenant {active_tenant.id}")
    return [RoleList.model_validate(role_data) for role_data in roles_with_count]


@router.post("/", response_model=RoleDetail, status_code=status.HTTP_201_CREATED)
async def create_custom_role_in_tenant(
    *,
    tenant: Tenant = Depends(get_tenant_from_path),
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:create")),
):
    """Create a new custom role within the specified tenant."""
    try:
        new_role = await role_service.create_custom_role(
            db, obj_in=role_in, tenant_id=tenant.id
        )
        role_detail = await role_service.get_role_with_permissions(db, role_id=new_role.id)
        if not role_detail:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve created role details.")
        return RoleDetail.model_validate(role_detail)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating role in tenant {tenant.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create role.")


@router.get(
    "/{role_id}",
    response_model=RoleDetail
)
async def get_role_details(
    *,
    tenant: Tenant = Depends(get_tenant_from_path),
    role_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:read")),
):
    """Get details for a specific role (system or custom) accessible in the tenant,
       including its assigned permissions.
    """
    role = await role_service.get_role_with_permissions(db, role_id=role_id)

    if not role or (not role.is_system_role and role.tenant_id != tenant.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or not accessible in this tenant")

    return RoleDetail.model_validate(role)


@router.patch(
    "/{role_id}",
    response_model=RoleDetail
)
async def update_custom_role_in_tenant(
    *,
    tenant: Tenant = Depends(get_tenant_from_path),
    role_id: UUID = Path(...),
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:update")),
):
    """Update a custom role's name, description, or permissions within the tenant.
       Cannot update system roles.
    """
    role = await role_service.get(db, record_id=role_id)
    if not role or role.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom role not found in this tenant")
    if role.is_system_role:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system roles.")

    try:
        updated_role = await role_service.update_custom_role(db, db_obj=role, obj_in=role_in)
        role_detail = await role_service.get_role_with_permissions(db, role_id=updated_role.id)
        if not role_detail:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated role details.")
        return RoleDetail.model_validate(role_detail)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating role {role_id} in tenant {tenant.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update role.")


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_custom_role_from_tenant(
    *,
    tenant: Tenant = Depends(get_tenant_from_path),
    role_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:delete")),
):
    """Delete a custom role from the tenant.
       Fails if the role is a system role or has users assigned.
    """
    deleted_role = await role_service.delete_custom_role(db, role_id=role_id, tenant_id=tenant.id)
    if deleted_role is None:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom role not found, is a system role, or has users assigned in this tenant")
    return None


# Note: This endpoint lists global permissions, but access is controlled by ROLE_READ in the active tenant.
@router.get("/permissions", response_model=List[PermissionSchema],
    summary="List Available Permissions",
    description="Lists all available permissions defined in the system.",
    # TODO: Consider if a more specific permission like SYSTEM_READ_PERMISSIONS is better long-term.
    dependencies=[Depends(require_permission_in_active_tenant(Permission.ROLE_READ))])
async def list_available_permissions(
    *,
    db: AsyncSession = Depends(get_db),
    # _: User = Depends(...) # User implicitly checked by permission dependency
    active_tenant: Tenant = Depends(get_current_active_tenant) # Still need tenant context for permission check
):
    """List all available permissions in the system, requires ROLE_READ in active tenant."""
    logger.info(f"Listing all available permissions (accessed via active tenant {active_tenant.id})")
    # Permissions themselves are global, service layer fetches all.
    permissions = await permission_service.get_multi(db, skip=0, limit=1000)
    logger.debug(f"Returning {len(permissions)} available permissions.")
    return permissions


@router.get(
    "/{role_id}/users",
    response_model=RoleUserAssignmentOutput,
    # Remove dependencies as tenant context/access is checked implicitly/manually
)
async def get_assigned_users_for_role(
    *,
    tenant: Tenant = Depends(get_tenant_from_path),
    role_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Get the list of user IDs assigned to a specific role within this tenant."""
    role = await role_service.get(db, record_id=role_id)
    if not role or (not role.is_system_role and role.tenant_id != tenant.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or not accessible in this tenant")

    users = await role_service.get_users_for_role(db, role_id=role_id, tenant_id=tenant.id)
    user_ids = [user.id for user in users]
    return RoleUserAssignmentOutput(user_ids=user_ids)


@router.put(
    "/{role_id}/users",
    response_model=RoleUserAssignmentOutput,
    # Remove dependencies as tenant context/access is checked implicitly/manually
)
async def set_assigned_users_for_role(
    *,
    tenant: Tenant = Depends(get_tenant_from_path),
    role_id: UUID = Path(...),
    assignment_in: RoleUserAssignmentInput,
    db: AsyncSession = Depends(get_db),
):
    """Set the complete list of users assigned to a role within this tenant.
       Replaces the existing assignments for this role in this tenant.
    """
    assigned_ids = await role_service.set_users_for_role(
        db, role_id=role_id, tenant_id=tenant.id, user_ids=assignment_in.user_ids
    )
    return RoleUserAssignmentOutput(user_ids=assigned_ids)

import logging
logger = logging.getLogger(__name__)
