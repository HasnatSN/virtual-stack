from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.models.iam.role import TenantRole, TenantRolePermission
from virtualstack.models.iam.permission import Permission
from virtualstack.models.iam.user import UserTenantRole
from virtualstack.services.base import CRUDBase


class RoleService(CRUDBase[TenantRole, Dict[str, Any], Dict[str, Any]]):
    """
    Service for tenant role management.
    """
    
    async def get_by_name(
        self, 
        db: AsyncSession, 
        *, 
        name: str, 
        tenant_id: UUID
    ) -> Optional[TenantRole]:
        """
        Get a role by name and tenant ID.
        
        Args:
            db: Database session
            name: Role name
            tenant_id: Tenant ID
            
        Returns:
            Role or None
        """
        stmt = select(self.model).where(
            and_(
                self.model.name == name,
                self.model.tenant_id == tenant_id
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()
    
    async def get_by_tenant(
        self, 
        db: AsyncSession, 
        *, 
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[TenantRole]:
        """
        Get all roles for a tenant.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of roles
        """
        stmt = select(self.model).where(
            self.model.tenant_id == tenant_id
        ).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_role_permissions(
        self, 
        db: AsyncSession, 
        *, 
        role_id: UUID
    ) -> List[Permission]:
        """
        Get all permissions for a role.
        
        Args:
            db: Database session
            role_id: Role ID
            
        Returns:
            List of permissions
        """
        stmt = select(Permission).join(
            TenantRolePermission,
            TenantRolePermission.permission_id == Permission.id
        ).where(
            TenantRolePermission.role_id == role_id
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def add_permission_to_role(
        self, 
        db: AsyncSession, 
        *, 
        role_id: UUID, 
        permission_id: UUID
    ) -> TenantRolePermission:
        """
        Add a permission to a role.
        
        Args:
            db: Database session
            role_id: Role ID
            permission_id: Permission ID
            
        Returns:
            Created role-permission association
        """
        # Check if the association already exists
        stmt = select(TenantRolePermission).where(
            and_(
                TenantRolePermission.role_id == role_id,
                TenantRolePermission.permission_id == permission_id
            )
        )
        result = await db.execute(stmt)
        existing = result.scalars().first()
        
        if existing:
            return existing
            
        # Create new association
        db_obj = TenantRolePermission(
            role_id=role_id,
            permission_id=permission_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def remove_permission_from_role(
        self, 
        db: AsyncSession, 
        *, 
        role_id: UUID, 
        permission_id: UUID
    ) -> bool:
        """
        Remove a permission from a role.
        
        Args:
            db: Database session
            role_id: Role ID
            permission_id: Permission ID
            
        Returns:
            True if removed, False if not found
        """
        stmt = select(TenantRolePermission).where(
            and_(
                TenantRolePermission.role_id == role_id,
                TenantRolePermission.permission_id == permission_id
            )
        )
        result = await db.execute(stmt)
        db_obj = result.scalars().first()
        
        if not db_obj:
            return False
            
        await db.delete(db_obj)
        await db.commit()
        return True
    
    async def get_user_roles(
        self, 
        db: AsyncSession, 
        *, 
        user_id: UUID, 
        tenant_id: Optional[UUID] = None
    ) -> List[TenantRole]:
        """
        Get all roles for a user, optionally filtered by tenant.
        
        Args:
            db: Database session
            user_id: User ID
            tenant_id: Optional tenant ID filter
            
        Returns:
            List of roles
        """
        stmt = select(TenantRole).join(
            UserTenantRole,
            UserTenantRole.role_id == TenantRole.id
        )
        
        # Add conditions
        conditions = [UserTenantRole.user_id == user_id]
        if tenant_id:
            conditions.append(UserTenantRole.tenant_id == tenant_id)
            
        stmt = stmt.where(and_(*conditions))
        
        result = await db.execute(stmt)
        return list(result.scalars().all())


# Create a singleton instance
role_service = RoleService(TenantRole) 