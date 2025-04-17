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

DEFAULT_ROLE_NAME = "Default User Role" # Define default role name constant

class UserService(CRUDBase[User, UserCreate, UserUpdate]):
    """Service for user management."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get a user by email (globally)."""
        stmt = select(self.model).where(self.model.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate, tenant_id: UUID, autocommit: bool = False) -> User:
        logger.debug(f"[UserService.create] ENTER - Email: {obj_in.email}, Tenant ID: {tenant_id}")
        db_user = None # Initialize db_user
        # 1. Create the User object
        try:
            hashed_password = create_password_hash(obj_in.password)
            logger.debug(f"[UserService.create] Password hashed for {obj_in.email}")
            # Construct full_name from first_name and last_name
            full_name = f"{obj_in.first_name} {obj_in.last_name}".strip()
            db_user = User(
                email=obj_in.email,
                hashed_password=hashed_password,
                full_name=full_name, # Use full_name matching the model column
                is_superuser=obj_in.is_superuser,
                is_active=obj_in.is_active,
            )
            logger.debug(f"[UserService.create] User object created for {obj_in.email} (full_name='{full_name}'). Adding to session...")
            db.add(db_user)  # EXPLICITLY add user to session
            logger.debug(f"[UserService.create] User object for {obj_in.email} added to session. Flushing...")
            # Flush to get the user ID without committing the transaction
            await db.flush()
            logger.debug(f"[UserService.create] Flush successful for {obj_in.email}. Refreshing ID...")
            await db.refresh(db_user, attribute_names=['id']) # Refresh just the ID
            logger.info(f"[UserService.create] User record flushed for {obj_in.email}. ID: {db_user.id}")

        except IntegrityError as e:
            logger.error(f"[UserService.create] IntegrityError during user flush for {obj_in.email}: {e}", exc_info=True)
            await db.rollback() # Rollback if flush fails
            if "users_email_key" in str(e).lower():
                 raise ValidationError(f"User with email {obj_in.email} already exists.")
            else:
                 raise
        except Exception as e:
            logger.error(f"[UserService.create] Exception during user flush for {obj_in.email}: {e}", exc_info=True)
            await db.rollback()
            # Ensure db_user is None if creation failed before flush
            db_user = None
            raise

        # Ensure user creation succeeded
        if not db_user or not db_user.id:
             logger.error("[UserService.create] User object or ID is missing after flush. Aborting tenant association.")
             # Consider raising a specific error here
             raise RuntimeError("Failed to create user record properly.")

        # 2. Fetch the Default Role ID
        logger.debug(f"[UserService.create] Fetching default role ID for name: {DEFAULT_ROLE_NAME}")
        default_role = await role_service.get_by_name_in_tenant(db, name=DEFAULT_ROLE_NAME, tenant_id=tenant_id)
        if not default_role:
             logger.error(f"[UserService.create] Default role '{DEFAULT_ROLE_NAME}' not found in tenant {tenant_id}! Cannot assign role to new user {db_user.id}.")
             # Depending on requirements, we might rollback the user creation or raise
             # For now, let's raise an error as association is likely required.
             # Consider rolling back the user creation if it should be atomic with role assignment
             # await db.rollback() # Potentially rollback user creation here
             raise ValueError(f"Default role '{DEFAULT_ROLE_NAME}' not found in tenant {tenant_id}.")
        default_role_id = default_role.id
        logger.debug(f"[UserService.create] Found default role ID: {default_role_id}")

        # 3. Create the TenantUserAssociation WITH Role ID
        logger.debug(f"[UserService.create] Creating tenant association for user {db_user.id}, tenant {tenant_id}, role {default_role_id}...")
        try:
            db_assoc = UserTenantRole(
                user_id=db_user.id,
                tenant_id=tenant_id,
                role_id=default_role_id # Include the role_id
            )
            logger.debug(f"[UserService.create] Association object created. Adding to session...")
            db.add(db_assoc)  # EXPLICITLY add association to session
            logger.debug(f"[UserService.create] Association added to session for user {db_user.id}. Flushing...")
            await db.flush() # Flush the association
            logger.info(f"[UserService.create] Tenant association flushed for user {db_user.id}, tenant {tenant_id}, role {default_role_id}.")
        except IntegrityError as e:
            logger.error(f"[UserService.create] IntegrityError during tenant association flush for user {db_user.id}, tenant {tenant_id}, role {default_role_id}: {e}", exc_info=True)
            await db.rollback()
            # Raise the original custom ValidationError (assuming it only takes message)
            raise ValidationError(f"Could not associate user with tenant {tenant_id} and role {default_role_id}. Invalid tenant/role or duplicate entry?") from e
        except Exception as e:
            logger.error(f"[UserService.create] Exception during tenant association flush for user {db_user.id}, tenant {tenant_id}, role {default_role_id}: {e}", exc_info=True)
            await db.rollback()
            raise

        # Only commit if explicitly requested
        if autocommit:
            logger.debug(f"[UserService.create] Autocommit=True, committing transaction...")
            await db.commit()
            
        logger.debug(f"[UserService.create] EXIT - Returning user {db_user.id}")
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
        users: List[User] = users_result.scalars().all()

        # --- Fetch Roles for the retrieved users --- #
        user_roles_map: Dict[UUID, List[str]] = {}
        if users:
            user_ids = [user.id for user in users]
            roles_stmt = (
                select(UserTenantRole.user_id, Role.name)
                .join(Role, UserTenantRole.role_id == Role.id)
                .where(
                    UserTenantRole.tenant_id == tenant_id,
                    UserTenantRole.user_id.in_(user_ids)
                )
            )
            roles_result = await db.execute(roles_stmt)
            for user_id, role_name in roles_result.all():
                if user_id not in user_roles_map:
                    user_roles_map[user_id] = []
                user_roles_map[user_id].append(role_name)

        # Attach roles to user objects (dynamically adding attribute for schema mapping)
        for user in users:
            user.roles = user_roles_map.get(user.id, []) # Add roles attribute

        # TODO: Ensure the User schema validation handles the dynamically added 'roles' attribute correctly.
        #       Since model_config has from_attributes=True, it should work.

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

    async def delete(self, db: AsyncSession, *, record_id: UUID, tenant_id: UUID, autocommit: bool = False) -> int:
        """Removes a user's association with a specific tenant. Returns number of associations removed (0 or 1)."""
        # TODO: Check if user has critical roles before removing association?
        # TODO: What happens if user has resources in this tenant? Should this be allowed?
        stmt = (
            delete(UserTenantRole)
            .where(UserTenantRole.user_id == record_id)
            .where(UserTenantRole.tenant_id == tenant_id)
        )
        result = await db.execute(stmt)
        if autocommit:
            await db.commit()
        # If result.rowcount is 0, it means the association didn't exist.
        # Consider raising NotFoundError if the association was expected to exist?
        if result.rowcount == 0:
            logger.warning(f"Attempted to delete non-existent tenant association for user {record_id} in tenant {tenant_id}")
            # Optionally raise error: raise NotFoundError("User association with tenant not found.")
        return result.rowcount

    async def assign_role_to_user_in_tenant(
        self, db: AsyncSession, *, user_id: UUID, role_id: UUID, tenant_id: UUID, autocommit: bool = False
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
            if autocommit:
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
        self, db: AsyncSession, *, user_id: UUID, role_id: UUID, tenant_id: UUID, autocommit: bool = False
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
        if autocommit:
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
