from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from datetime import datetime

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, insert, delete, and_, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import logging # Import logging
from sqlalchemy.orm import joinedload

from virtualstack.core.security import create_password_hash, verify_password
from virtualstack.models.iam.user import User
from virtualstack.models.iam.user_tenant_role import user_tenant_roles_table, UserTenantRole
from virtualstack.models.iam.role import Role
from virtualstack.schemas.iam.user import UserCreate, UserUpdate
from virtualstack.services.base import CRUDBase
from virtualstack.services.iam import role_service # Add import for role_service
from virtualstack.services.iam import tenant_service # Add import for tenant_service
from virtualstack.core.exceptions import AuthorizationError, ValidationError

logger = logging.getLogger(__name__) # Setup logger

class UserService(CRUDBase[User, UserCreate, UserUpdate]):
    """Service for user management."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get a user by email."""
        stmt = select(self.model).where(self.model.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create a new user."""
        # TODO: Consider if additional validation is needed here (e.g., unique email checked by DB)
        db_obj = User(
            email=obj_in.email,
            hashed_password=create_password_hash(obj_in.password), # Ensure create_password_hash is used
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            is_superuser=obj_in.is_superuser,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: Union[UserUpdate, dict[str, Any]]
    ) -> User:
        """Update a user."""
        # Use model_dump for Pydantic V2 compatibility
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        if "password" in update_data and update_data["password"]:
            # Hash the new password if provided
            plain_password = update_data.pop("password")
            # TODO: Validate password complexity requirements if needed
            update_data["hashed_password"] = create_password_hash(plain_password)

        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def assign_role_to_user_in_tenant(
        self, db: AsyncSession, *, user_id: UUID, role_id: UUID, tenant_id: UUID
    ) -> bool:
        """Assigns a role to a user within a tenant. Returns True if assigned, False if already exists."""
        # TODO: Add validation - Check if Role exists and belongs to the tenant?
        # Check if the assignment already exists
        existing_assignment = await db.execute(
            select(UserTenantRole)
            .where(UserTenantRole.user_id == user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
            .where(UserTenantRole.role_id == role_id)
        )
        if existing_assignment.scalar_one_or_none():
            return False # Indicate idempotency: assignment already exists

        # Create the new assignment
        new_assignment = UserTenantRole(
            user_id=user_id,
            tenant_id=tenant_id,
            role_id=role_id
        )
        db.add(new_assignment)
        await db.commit() 
        # No refresh needed for association object unless it has server defaults
        return True # Indicate successful assignment

    async def remove_role_from_user_in_tenant(
        self, db: AsyncSession, *, user_id: UUID, role_id: UUID, tenant_id: UUID
    ) -> int:
        """Removes a specific role assignment from a user within a tenant. Returns the number of rows deleted."""
        # TODO: Add validation? Should we check if user/role/tenant exist first?
        stmt = (
            delete(UserTenantRole)
            .where(UserTenantRole.user_id == user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
            .where(UserTenantRole.role_id == role_id)
        )
        result = await db.execute(stmt)
        await db.commit() 
        return result.rowcount # Returns the number of rows deleted (0 or 1)

    async def is_user_in_tenant(self, db: AsyncSession, *, user_id: UUID, tenant_id: UUID) -> bool:
        """Check if a user has any roles assigned within a specific tenant."""
        stmt = (
            select(UserTenantRole.user_id)
            .where(UserTenantRole.user_id == user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_users_by_tenant(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Retrieve users associated with a specific tenant (have roles in the tenant)."""
        stmt = (
            select(User).distinct()
            .join(UserTenantRole, User.id == UserTenantRole.user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_user_roles_in_tenant(
        self, db: AsyncSession, *, user_id: UUID, tenant_id: UUID
    ) -> List[Role]:
        """Retrieve all roles assigned to a user within a specific tenant."""
        stmt = (
            select(Role)
            .join(UserTenantRole, Role.id == UserTenantRole.role_id)
            .where(UserTenantRole.user_id == user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_user_permissions_in_tenant(
        self, db: AsyncSession, *, user_id: UUID, tenant_id: UUID
    ) -> List[str]:
        """Retrieve all permission names assigned to a user within a specific tenant via their roles."""
        # TODO: Implement this logic by joining User -> UserTenantRole -> Role -> RolePermission -> Permission
        # Placeholder implementation
        # This needs a more complex query involving joins across multiple tables
        # or potentially multiple queries depending on optimization strategy.
        return []

    async def get_users_by_tenant_with_roles(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100, search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve users associated with a specific tenant with their roles.
        
        Args:
            db: Database session
            tenant_id: Tenant ID to filter users
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (for pagination)
            search: Optional search string to filter users by name or email
            
        Returns:
            List of dictionaries containing user data and their roles
        """
        # First get the distinct users in this tenant
        user_query = (
            select(User).distinct()
            .join(UserTenantRole, User.id == UserTenantRole.user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
        )
        
        # Apply search if provided
        if search:
            search_term = f"%{search}%"
            user_query = user_query.where(
                (User.email.ilike(search_term)) |
                (User.first_name.ilike(search_term)) |
                (User.last_name.ilike(search_term))
            )
        
        # Apply pagination
        user_query = user_query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(user_query)
        users = result.scalars().all()
        
        # For each user, get their roles in this tenant
        user_role_data = []
        for user in users:
            roles = await self.get_user_roles_in_tenant(db, user_id=user.id, tenant_id=tenant_id)
            role_names = [role.name for role in roles]
            
            # Create a dictionary with user data and roles
            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "roles": role_names
            }
            user_role_data.append(user_data)
        
        return user_role_data

user_service = UserService(User)
