from typing import Any, List, Optional

from fastapi import APIRouter, Depends, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from virtualstack.api.deps import get_current_user
from virtualstack.core.exceptions import (
    http_not_found_error, 
    http_validation_error
)
from virtualstack.db.session import get_db
from virtualstack.models.iam.tenant import Tenant
from virtualstack.schemas.iam.tenant import Tenant as TenantSchema, TenantCreate, TenantUpdate
from virtualstack.services.iam import tenant_service

router = APIRouter()


@router.get("/", response_model=List[TenantSchema])
async def get_tenants(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """
    Retrieve tenants.
    """
    tenants = await tenant_service.get_multi(db, skip=skip, limit=limit)
    return tenants


@router.post("/", response_model=TenantSchema, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_in: TenantCreate,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Create a new tenant.
    """
    # Check if tenant with this name already exists
    existing_tenant = await tenant_service.get_by_name(db, name=tenant_in.name)
    if existing_tenant:
        raise http_validation_error(detail=f"Tenant with name {tenant_in.name} already exists")
    
    # Create the tenant
    tenant = await tenant_service.create(db, obj_in=tenant_in)
    return tenant


@router.get("/{tenant_id}", response_model=TenantSchema)
async def get_tenant_by_id(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Path(...),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get tenant by ID.
    """
    tenant = await tenant_service.get(db, id=tenant_id)
    if not tenant:
        raise http_not_found_error(detail="Tenant not found")
    return tenant


@router.get("/slug/{slug}", response_model=TenantSchema)
async def get_tenant_by_slug(
    *,
    db: AsyncSession = Depends(get_db),
    slug: str = Path(...),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get tenant by slug.
    """
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
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Update tenant information.
    """
    tenant = await tenant_service.get(db, id=tenant_id)
    if not tenant:
        raise http_not_found_error(detail="Tenant not found")
    
    # Update the tenant
    tenant = await tenant_service.update(db, db_obj=tenant, obj_in=tenant_in)
    return tenant


@router.delete("/{tenant_id}", response_model=TenantSchema, status_code=status.HTTP_200_OK)
async def delete_tenant(
    *,
    db: AsyncSession = Depends(get_db),
    tenant_id: UUID = Path(...),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Delete a tenant.
    """
    tenant = await tenant_service.get(db, id=tenant_id)
    if not tenant:
        raise http_not_found_error(detail="Tenant not found")
    
    # Delete the tenant
    tenant = await tenant_service.delete(db, id=tenant_id)
    return tenant 