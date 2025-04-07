from typing import Any, Dict, List, Optional, Union, Tuple
from uuid import UUID
from datetime import datetime

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, insert, delete, and_, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import logging # Import logging
from sqlalchemy.orm import joinedload

from virtualstack.core.security import create_password_hash, verify_password
from virtualstack.models.iam.user import User
from virtualstack.models.iam.user_tenant_role import UserTenantRole
from virtualstack.models.iam.role import Role
from virtualstack.schemas.iam.user import UserCreate, UserUpdate
from virtualstack.services.base import CRUDBase
from virtualstack.services.iam import role_service # Add import for role_service
from virtualstack.services.iam import tenant_service # Add import for tenant_service
from virtualstack.core.exceptions import AuthorizationError, ValidationError, NotFoundError

logger = logging.getLogger(__name__) # Setup logger

class UserService(CRUDBase[User, UserCreate, UserUpdate]):
    """Service for user management."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get a user by email (globally)."""
        stmt = select(self.model).where(self.model.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate, tenant_id: UUID) -> User:
        """Create a new user and associate them with the specified tenant."""
        # 1. Create the User object
        db_user = User(
            email=obj_in.email,
            hashed_password=create_password_hash(obj_in.password),
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            is_superuser=obj_in.is_superuser,
            is_active=obj_in.is_active,
        )
        db.add(db_user)

        try:
            # Commit to get the user ID
            await db.commit()
            await db.refresh(db_user)
        except IntegrityError as e:
            await db.rollback()
            # Check if it's a unique constraint violation on email
            if "unique constraint" in str(e).lower() and "users_email_key" in str(e).lower():
                 raise ValidationError(f"User with email {obj_in.email} already exists.")
            else:
                 logger.error(f"Database integrity error creating user {obj_in.email}: {e}", exc_info=True)
                 raise # Re-raise other integrity errors
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating user {obj_in.email}: {e}", exc_info=True)
            raise

        # 2. Create the TenantUserAssociation
        # TODO: Should new users automatically get a default role in the tenant?
        #       If so, need to fetch the default role ID and add it here.
        #       For now, just associating user with tenant, no role assigned yet.
        db_assoc = UserTenantRole(user_id=db_user.id, tenant_id=tenant_id)
        db.add(db_assoc)

        try:
            await db.commit()
            # No refresh needed for association unless it has defaults
        except IntegrityError as e:
            await db.rollback()
            # This might happen if tenant_id is invalid (FK violation) or if the pair already exists (rare)
            logger.error(f"Error creating tenant association for user {db_user.id} and tenant {tenant_id}: {e}", exc_info=True)
            # Optional: Could attempt to delete the just-created user here for cleanup,
            # but might be better to let the caller handle the overall transaction.
            raise ValidationError(f"Could not associate user with tenant {tenant_id}. Invalid tenant?", error_type="tenant_association_failed")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error committing tenant association for user {db_user.id}: {e}", exc_info=True)
            raise

        return db_user

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: Union[UserUpdate, dict[str, Any]]
    ) -> User:
        """Update a user. Prevents updating hashed_password directly via dict."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        # Security: Prevent direct update of hashed_password if obj_in is a dictionary
        if isinstance(obj_in, dict) and "hashed_password" in update_data:
            del update_data["hashed_password"]
            logger.warning(f"Attempted direct update of hashed_password for user {db_obj.id} blocked.")

        if "password" in update_data and update_data["password"]:
            plain_password = update_data.pop("password")
            update_data["hashed_password"] = create_password_hash(plain_password)

        # Prevent making user inactive if they are the only active admin in a tenant?
        # TODO: Add check for is_active=False if needed.

        return await super().update(db, db_obj=db_obj, obj_in=update_data)

    async def get_multi_by_tenant_paginated(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100, search: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """Retrieve users associated with a tenant, with pagination and search.
           Returns a tuple: (list_of_users, total_count)
        """
        # Base query to select distinct users associated with the tenant
        base_query = (
            select(User)
            .join(UserTenantRole, User.id == UserTenantRole.user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
            .distinct()
        )

        # Apply search filter if provided
        if search:
            search_term = f"%{search.lower()}%"
            base_query = base_query.where(
                or_(
                    func.lower(User.email).contains(search_term),
                    func.lower(User.first_name).contains(search_term),
                    func.lower(User.last_name).contains(search_term),
                )
            )

        # Get total count matching the criteria *before* applying limit/offset
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total_count = total_result.scalar_one()

        # Apply ordering, offset, and limit for the final user list
        users_query = base_query.order_by(User.email).offset(skip).limit(limit)
        users_result = await db.execute(users_query)
        users = users_result.scalars().all()

        return users, total_count

    async def get_by_id_and_tenant(self, db: AsyncSession, *, record_id: UUID, tenant_id: UUID) -> Optional[User]:
        """Get a user by ID, but only if they are associated with the specified tenant."""
        stmt = (
            select(User)
            .join(UserTenantRole, User.id == UserTenantRole.user_id)
            .where(User.id == record_id)
            .where(UserTenantRole.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def delete(self, db: AsyncSession, *, record_id: UUID, tenant_id: UUID) -> int:
        """Removes a user's association with a specific tenant. Returns number of associations removed (0 or 1)."""
        # TODO: Check if user has critical roles before removing association?
        # TODO: What happens if user has resources in this tenant? Should this be allowed?
        stmt = (
            delete(UserTenantRole)
            .where(UserTenantRole.user_id == record_id)
            .where(UserTenantRole.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        await db.commit()
        # If result.rowcount is 0, it means the association didn't exist.
        # Consider raising NotFoundError if the association was expected to exist?
        if result.rowcount == 0:
            logger.warning(f"Attempted to delete non-existent tenant association for user {record_id} in tenant {tenant_id}")
            # Optionally raise error: raise NotFoundError("User association with tenant not found.")
        return result.rowcount

    async def assign_role_to_user_in_tenant(
        self, db: AsyncSession, *, user_id: UUID, role_id: UUID, tenant_id: UUID
    ) -> bool:
        """Assigns a role to a user within a tenant. Returns True if assigned, False if already exists."""
        # Validation: Check if user, role, and tenant exist and are related
        user = await self.get_by_id_and_tenant(db, record_id=user_id, tenant_id=tenant_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found in tenant {tenant_id}")
        role = await role_service.get_role_by_id_and_tenant(db, role_id=role_id, tenant_id=tenant_id)
        if not role:
            raise NotFoundError(f"Role {role_id} not found or not accessible in tenant {tenant_id}")

        # Check if the assignment already exists
        existing_assignment_stmt = (
            select(UserTenantRole.user_id)
            .where(UserTenantRole.user_id == user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
            .where(UserTenantRole.role_id == role_id)
            .limit(1)
        )
        existing = await db.execute(existing_assignment_stmt)
        if existing.scalar_one_or_none():
            return False # Assignment already exists

        # Create the new assignment
        new_assignment = UserTenantRole(user_id=user_id, tenant_id=tenant_id, role_id=role_id)
        db.add(new_assignment)
        try:
            await db.commit()
        except IntegrityError as e:
             await db.rollback()
             logger.error(f"Integrity error assigning role {role_id} to user {user_id} in tenant {tenant_id}: {e}", exc_info=True)
             # Could be FK violation if user/role/tenant deleted concurrently, or unique constraint if race condition
             raise ValidationError("Could not assign role due to database constraint.")
        except Exception as e:
            await db.rollback()
            logger.error(f"Error assigning role {role_id} to user {user_id} in tenant {tenant_id}: {e}", exc_info=True)
            raise

        return True

    async def remove_role_from_user_in_tenant(
        self, db: AsyncSession, *, user_id: UUID, role_id: UUID, tenant_id: UUID
    ) -> int:
        """Removes a specific role assignment from a user within a tenant. Returns rows deleted."""
        # Optional Validation: Check if user/role/tenant exist first?
        # user = await self.get_by_id_and_tenant(db, record_id=user_id, tenant_id=tenant_id)
        # if not user: ...
        # role = await role_service.get_role_by_id_and_tenant(db, role_id=role_id, tenant_id=tenant_id)
        # if not role: ...

        stmt = (
            delete(UserTenantRole)
            .where(UserTenantRole.user_id == user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
            .where(UserTenantRole.role_id == role_id)
        )
        result = await db.execute(stmt)
        await db.commit()
        if result.rowcount == 0:
             logger.warning(f"Attempted to remove non-existent role assignment: user={user_id}, role={role_id}, tenant={tenant_id}")
        return result.rowcount

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

    async def get_user_roles_in_tenant(
        self, db: AsyncSession, *, user_id: UUID, tenant_id: UUID
    ) -> List[Role]:
        """Retrieve all roles assigned to a user within a specific tenant."""
        # Ensure we only get roles associated via the correct tenant
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
        """Retrieve all unique permission names assigned to a user within a specific tenant via their roles."""
        # This query joins through user -> association -> role -> role_permission -> permission
        # and selects distinct permission names.
        from virtualstack.models.iam.permission import Permission as PermissionModel
        from virtualstack.models.iam.role_permission import RolePermission

        stmt = (
            select(PermissionModel.name).distinct()
            .join(RolePermission, PermissionModel.id == RolePermission.permission_id)
            .join(Role, RolePermission.role_id == Role.id)
            .join(UserTenantRole, Role.id == UserTenantRole.role_id)
            .where(UserTenantRole.user_id == user_id)
            .where(UserTenantRole.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        return result.scalars().all()

user_service = UserService(User)
