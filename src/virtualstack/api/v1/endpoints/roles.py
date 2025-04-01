from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import get_db, require_permission
from virtualstack.core.permissions import Permission
from virtualstack.schemas.iam import (
    Role,
    RoleCreate,
    RolePermissionCreate,
    RoleUpdate,
    RoleWithPermissions,
)
from virtualstack.services.iam import permission_service, role_service


router = APIRouter()


@router.get("/", response_model=list[Role])
async def list_roles(
    tenant_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission(Permission.ROLE_READ)),
):
    """List roles for a tenant."""
    return await role_service.get_by_tenant(db, tenant_id=tenant_id, skip=skip, limit=limit)


@router.post("/", response_model=Role, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission(Permission.ROLE_CREATE)),
):
    """Create a new role in a tenant."""
    # Check if role with same name already exists in tenant
    existing_role = await role_service.get_by_name(
        db, name=role_in.name, tenant_id=role_in.tenant_id
    )
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role with name '{role_in.name}' already exists in this tenant",
        )

    # Create the role
    return await role_service.create(db, obj_in=role_in)


@router.get("/{role_id}", response_model=RoleWithPermissions)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission(Permission.ROLE_READ)),
):
    """Get a specific role by ID."""
    role = await role_service.get(db, id=role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Get permissions for the role
    permissions = await role_service.get_role_permissions(db, role_id=role_id)

    # Return role with permissions
    role_data = Role.model_validate(role).model_dump()
    role_data["permissions"] = [p.name for p in permissions]
    return role_data


@router.put("/{role_id}", response_model=Role)
async def update_role(
    role_id: UUID,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission(Permission.ROLE_UPDATE)),
):
    """Update a role."""
    role = await role_service.get(db, id=role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Prevent updating system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system roles"
        )

    # Update the role
    return await role_service.update(db, db_obj=role, obj_in=role_in)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission(Permission.ROLE_DELETE)),
):
    """Delete a role."""
    role = await role_service.get(db, id=role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Prevent deleting system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system roles"
        )

    # Delete the role
    await role_service.remove(db, id=role_id)


@router.post("/{role_id}/permissions", response_model=RoleWithPermissions)
async def add_permission_to_role(
    role_id: UUID,
    permission_in: RolePermissionCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission(Permission.PERMISSION_ASSIGN)),
):
    """Add a permission to a role."""
    role = await role_service.get(db, id=role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    permission = await permission_service.get(db, id=permission_in.permission_id)
    if not permission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    # Add permission to role
    await role_service.add_permission_to_role(
        db, role_id=role_id, permission_id=permission_in.permission_id
    )

    # Get updated permissions for the role
    permissions = await role_service.get_role_permissions(db, role_id=role_id)

    # Return role with updated permissions
    role_data = Role.model_validate(role).model_dump()
    role_data["permissions"] = [p.name for p in permissions]
    return role_data


@router.delete("/{role_id}/permissions/{permission_id}")
async def remove_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission(Permission.PERMISSION_ASSIGN)),
):
    """Remove a permission from a role."""
    role = await role_service.get(db, id=role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Remove permission from role
    result = await role_service.remove_permission_from_role(
        db, role_id=role_id, permission_id=permission_id
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not assigned to this role"
        )

    # Get updated permissions for the role
    permissions = await role_service.get_role_permissions(db, role_id=role_id)

    # Return role with updated permissions
    role_data = Role.model_validate(role).model_dump()
    role_data["permissions"] = [p.name for p in permissions]
    return role_data
