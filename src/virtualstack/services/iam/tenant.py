from typing import Optional, Any, Dict, Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.models.iam.tenant import Tenant
from virtualstack.schemas.iam.tenant import TenantCreate, TenantUpdate
from virtualstack.services.base import CRUDBase


class TenantService(CRUDBase[Tenant, TenantCreate, TenantUpdate]):
    """
    Service for tenant management.
    """
    
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Tenant]:
        """
        Get a tenant by name.
        """
        stmt = select(self.model).where(self.model.name == name)
        result = await db.execute(stmt)
        return result.scalars().first()
    
    async def get_by_slug(self, db: AsyncSession, *, slug: str) -> Optional[Tenant]:
        """
        Get a tenant by slug.
        """
        stmt = select(self.model).where(self.model.slug == slug)
        result = await db.execute(stmt)
        return result.scalars().first()
    
    async def create(self, db: AsyncSession, *, obj_in: TenantCreate) -> Tenant:
        """
        Create a new tenant.
        """
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Tenant,
        obj_in: Union[TenantUpdate, Dict[str, Any]]
    ) -> Tenant:
        """
        Update a tenant.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
            
        return await super().update(db, db_obj=db_obj, obj_in=update_data)


tenant_service = TenantService(Tenant) 