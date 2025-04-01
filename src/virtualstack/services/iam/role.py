from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.models.iam.permission import Permission

# from virtualstack.models.iam.role import TenantRole, TenantRolePermission # TODO: Implement these models
from virtualstack.models.iam.role import Role

# from virtualstack.models.iam.user import UserTenantRole # TODO: Implement this model
from virtualstack.services.base import CRUDBase


class RoleService(CRUDBase[Role, dict[str, Any], dict[str, Any]]):
    """Service for tenant role management."""

    async def get_by_name(self, db: AsyncSession, *, name: str, tenant_id: UUID) -> Optional[Role]:
        """Get a role by name and tenant ID.

        Args:
            db: Database session
            name: Role name
            tenant_id: Tenant ID

        Returns:
            Role or None
        """
        stmt = select(self.model).where(
            and_(self.model.name == name, self.model.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_tenant(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Role]:
        """Get all roles for a tenant.

        Args:
            db: Database session
            tenant_id: Tenant ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of roles
        """
        stmt = select(self.model).where(self.model.tenant_id == tenant_id).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_permissions(self, *, role_id: UUID) -> list[Permission]:
        """Get all permissions for a role.

        Args:
            role_id: Role ID

        Returns:
            List of permissions
        """
        # TODO: Implement using the correct association table model once created (will use role_id)
        return []

    async def add_permission_to_role(
        self, *, role_id: UUID, permission_id: UUID
    ) -> Any:
        """Add a permission to a role.

        Args:
            role_id: Role ID
            permission_id: Permission ID

        Returns:
            Created role-permission association (or placeholder)
        """
        # TODO: Implement using the correct association table model once created (will use role_id, permission_id)
        return None

    async def remove_permission_from_role(self, *, role_id: UUID, permission_id: UUID) -> bool:
        """Remove a permission from a role.

        Args:
            role_id: Role ID
            permission_id: Permission ID

        Returns:
            True if removed, False if not found
        """
        # TODO: Implement using the correct association table model once created (will use role_id, permission_id)
        return False

    async def get_user_roles(
        self, *, user_id: UUID, tenant_id: Optional[UUID] = None
    ) -> list[Role]:
        """Get all roles for a user, optionally filtered by tenant.

        Args:
            user_id: User ID
            tenant_id: Optional tenant ID filter

        Returns:
            List of roles
        """
        # TODO: Implement using the correct association table model once created (will use user_id, tenant_id)
        return []


# Create a singleton instance
role_service = RoleService(Role)
