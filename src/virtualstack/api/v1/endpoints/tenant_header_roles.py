from uuid import UUID
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import get_db, require_permission, get_current_active_user, get_validated_tenant_id
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


router = APIRouter()

# TODO: Add pagination for users and error handling throughout
# TODO: Add search capability for roles and users

@router.get("/", response_model=List[RoleList])
async def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _: User = Depends(require_permission(Permission.ROLE_READ)),
):
    """List roles (system & custom) available within the tenant derived from the header.
       Includes the count of users assigned to each role in this tenant.
    """
    roles_with_count = await role_service.get_multi_by_tenant_with_user_count(
        db, tenant_id=tenant_id, skip=skip, limit=limit
    )
    return [RoleList.model_validate(role_data) for role_data in roles_with_count]


@router.post("/", response_model=RoleDetail, status_code=status.HTTP_201_CREATED)
async def create_custom_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _: User = Depends(require_permission(Permission.ROLE_CREATE)),
):
    """Create a new custom role within the tenant derived from the header."""
    try:
        new_role = await role_service.create_custom_role(
            db, obj_in=role_in, tenant_id=tenant_id
        )
        role_detail = await role_service.get_role_with_permissions(db, role_id=new_role.id)
        if not role_detail:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve created role details.")
        return RoleDetail.model_validate(role_detail)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not create role: {str(e)}")


@router.get(
    "/{role_id}",
    response_model=RoleDetail
)
async def get_role_details(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _: User = Depends(require_permission(Permission.ROLE_READ)),
):
    """Get details for a specific role (system or custom) accessible in the tenant,
       including its assigned permissions.
    """
    role = await role_service.get_role_with_permissions(db, role_id=role_id)

    if not role or (not role.is_system_role and role.tenant_id != tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or not accessible in this tenant")

    return RoleDetail.model_validate(role)


@router.patch(
    "/{role_id}",
    response_model=RoleDetail
)
async def update_custom_role(
    role_id: UUID,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _: User = Depends(require_permission(Permission.ROLE_UPDATE)),
):
    """Update a custom role's name, description, or permissions within the tenant.
       Cannot update system roles.
    """
    role = await role_service.get(db, record_id=role_id)
    if not role or role.tenant_id != tenant_id:
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not update role: {str(e)}")


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_custom_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _: User = Depends(require_permission(Permission.ROLE_DELETE)),
):
    """Delete a custom role from the tenant.
       Fails if the role is a system role or has users assigned.
    """
    deleted_role = await role_service.delete_custom_role(db, role_id=role_id, tenant_id=tenant_id)
    if deleted_role is None:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom role not found in this tenant")
    return None


@router.get("/permissions", response_model=List[PermissionSchema])
async def list_available_permissions(
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _: User = Depends(require_permission(Permission.ROLE_READ)), 
):
    """List all available permissions in the system.
       (Permissions themselves are global, not tenant-specific).
    """
    return await permission_service.get_multi(db, skip=0, limit=1000)


@router.get(
    "/{role_id}/users",
    response_model=RoleUserAssignmentOutput,
    dependencies=[Depends(require_permission(Permission.ROLE_READ)), Depends(require_permission(Permission.USER_READ))]
)
async def get_assigned_users_for_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Get the list of user IDs assigned to a specific role within this tenant."""
    role = await role_service.get(db, record_id=role_id)
    if not role or (not role.is_system_role and role.tenant_id != tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or not accessible in this tenant")
    
    users = await role_service.get_users_for_role(db, role_id=role_id, tenant_id=tenant_id)
    user_ids = [user.id for user in users]
    return RoleUserAssignmentOutput(user_ids=user_ids)


@router.put(
    "/{role_id}/users",
    response_model=RoleUserAssignmentOutput,
    dependencies=[Depends(require_permission(Permission.ROLE_ASSIGN))] 
)
async def set_assigned_users_for_role(
    role_id: UUID,
    assignment_in: RoleUserAssignmentInput,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Set the complete list of users assigned to a role within this tenant.
       Replaces the existing assignments for this role in this tenant.
    """
    assigned_ids = await role_service.set_users_for_role(
        db, role_id=role_id, tenant_id=tenant_id, user_ids=assignment_in.user_ids
    )
    return RoleUserAssignmentOutput(user_ids=assigned_ids) 