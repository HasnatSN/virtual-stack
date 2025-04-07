from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import get_current_user
from virtualstack.core.exceptions import http_not_found_error, http_validation_error
from virtualstack.db.session import get_db
from virtualstack.models.iam.user import User
from virtualstack.schemas.iam.tenant import Tenant as TenantSchema
from virtualstack.schemas.iam.tenant import TenantCreate, TenantUpdate
from virtualstack.services.iam import tenant_service


router = APIRouter()


@router.get(
    "/",
    response_model=list[TenantSchema],
    dependencies=[Depends(get_current_user)]
)
async def list_accessible_tenants(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[TenantSchema]:
    """Retrieve tenants accessible to the current authenticated user."""
    return await tenant_service.get_multi_by_user(db, user_id=current_user.id)


@router.post("/", response_model=TenantSchema, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_in: TenantCreate,
) -> Any:
    """Create a new tenant."""
    # Check if tenant with this name already exists
    existing_tenant = await tenant_service.get_by_name(db, name=tenant_in.name)
    if existing_tenant:
        raise http_validation_error(detail=f"Tenant with name {tenant_in.name} already exists")

    # Create the tenant
    return await tenant_service.create(db, obj_in=tenant_in)


@router.get("/{tenant_id}", response_model=TenantSchema)
async def get_tenant_by_id(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Path(...),
) -> Any:
    """Get tenant by ID."""
    tenant = await tenant_service.get(db, record_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.get("/slug/{slug}", response_model=TenantSchema)
async def get_tenant_by_slug(
    *,
    db: AsyncSession = Depends(get_db),
    slug: str = Path(...),
) -> Any:
    """Get tenant by slug."""
    tenant = await tenant_service.get_by_slug(db, slug=slug)
    if not tenant:
        raise http_not_found_error(detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}", response_model=TenantSchema)
async def update_tenant(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Path(...),
    tenant_in: TenantUpdate,
) -> Any:
    """Update tenant information."""
    tenant = await tenant_service.get(db, record_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    updated_tenant = await tenant_service.update(db, db_obj=tenant, obj_in=tenant_in)
    return updated_tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Path(...),
) -> None:
    """Delete a tenant."""
    tenant = await tenant_service.get(db, record_id=tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    deleted_tenant = await tenant_service.delete(db, record_id=tenant_id)
    if not deleted_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found or already deleted",
        )
    return None


# TODO: Add tests for get_tenant_by_slug endpoint
# TODO: Implement proper authorization checks based on current_user roles/permissions
