from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.models.iam.permission import Permission
from virtualstack.services.base import CRUDBase


class PermissionService(CRUDBase[Permission, Dict[str, Any], Dict[str, Any]]):
    """
    Service for permission management.
    """
    
    async def get_by_name(
        self, 
        db: AsyncSession, 
        *, 
        name: str
    ) -> Optional[Permission]:
        """
        Get a permission by name.
        
        Args:
            db: Database session
            name: Permission name
            
        Returns:
            Permission or None
        """
        stmt = select(self.model).where(self.model.name == name)
        result = await db.execute(stmt)
        return result.scalars().first()
    
    async def get_by_names(
        self, 
        db: AsyncSession, 
        *, 
        names: List[str]
    ) -> List[Permission]:
        """
        Get permissions by names.
        
        Args:
            db: Database session
            names: List of permission names
            
        Returns:
            List of permissions
        """
        stmt = select(self.model).where(self.model.name.in_(names))
        result = await db.execute(stmt)
        return list(result.scalars().all())


# Create a singleton instance
permission_service = PermissionService(Permission) 