from typing import Any, Optional, List
from uuid import UUID
import logging

from sqlalchemy import and_, select, insert, delete, func, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError

from virtualstack.models.iam.permission import Permission
from virtualstack.models.iam.role import Role
from virtualstack.models.iam.role_permissions import role_permissions_table
from virtualstack.models.iam.user_tenant_role import user_tenant_roles_table
from virtualstack.models.iam.user import User
from virtualstack.services.base import CRUDBase
from virtualstack.schemas.iam.role import RoleCreate, RoleUpdate


logger = logging.getLogger(__name__)


class RoleService(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """Service for managing roles within a tenant context."""

    async def get_by_name_in_tenant(
        self, db: AsyncSession, *, name: str, tenant_id: UUID
    ) -> Optional[Role]:
        """Get a role by its name within a specific tenant."""
        stmt = select(self.model).where(
            self.model.name == name, self.model.tenant_id == tenant_id
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_multi_by_tenant(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Role]:
        """Get all roles (system + custom) accessible within a tenant."""
        # Select roles that are system roles OR belong to the specific tenant
        stmt = (
            select(self.model)
            .where(self.model.tenant_id == tenant_id | self.model.is_system_role == True)
            .order_by(self.model.name)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_multi_by_tenant_with_user_count(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        """Get roles for a tenant, including the count of users assigned to each role within that tenant."""
        # Subquery to count users per role *in this tenant*
        user_count_subq = (
            select(
                user_tenant_roles_table.c.role_id,
                func.count(user_tenant_roles_table.c.user_id).label("user_count"),
            )
            .where(user_tenant_roles_table.c.tenant_id == tenant_id)
            .group_by(user_tenant_roles_table.c.role_id)
            .subquery()
        )

        # Main query to get roles (system or tenant-specific)
        # Left join with the user count subquery
        stmt = (
            select(
                self.model.id,
                self.model.name,
                self.model.description,
                self.model.is_system_role,
                func.coalesce(user_count_subq.c.user_count, 0).label("user_count"),
            )
            .outerjoin(
                user_count_subq, self.model.id == user_count_subq.c.role_id
            )
            .where(self.model.tenant_id == tenant_id | self.model.is_system_role == True)
            .order_by(self.model.name)
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(stmt)
        # Use .mappings().all() to get results as list of dict-like objects
        return list(result.mappings().all())

    async def get_role_with_permissions(self, db: AsyncSession, *, role_id: UUID) -> Optional[Role]:
        """Get a specific role and eagerly load its associated permissions."""
        stmt = (
            select(self.model)
            .options(selectinload(self.model.permissions))
            .where(self.model.id == role_id)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create_custom_role(
        self, db: AsyncSession, *, obj_in: RoleCreate, tenant_id: UUID
    ) -> Role:
        """Create a new custom role for a specific tenant and assign initial permissions."""
        # Check for existing role name within the tenant
        existing_role = await self.get_by_name_in_tenant(db, name=obj_in.name, tenant_id=tenant_id)
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Role with name '{obj_in.name}' already exists in this tenant",
            )
        
        # Prepare role data, ensuring it's marked as non-system and linked to the tenant
        role_data = obj_in.model_dump(exclude={"permission_ids"}) # Exclude permissions for initial creation
        role_data["tenant_id"] = tenant_id
        role_data["is_system_role"] = False

        db_role = self.model(**role_data)
        db.add(db_role)
        await db.commit() # Commit to get the role ID
        # await db.refresh(db_role) # Refresh might not load permissions yet

        # Assign permissions if provided
        if obj_in.permission_ids:
            await self.set_role_permissions(db, role_id=db_role.id, permission_ids=obj_in.permission_ids)
            await db.commit() # Commit permission changes
        
        # Refresh again to load newly assigned permissions if needed by the caller
        # Alternatively, return the initially created object and let the endpoint fetch details if required
        await db.refresh(db_role, attribute_names=['permissions']) # Specify relationship to refresh

        return db_role

    async def update_custom_role(
        self, db: AsyncSession, *, db_obj: Role, obj_in: RoleUpdate
    ) -> Role:
        """Update a custom role's details and permissions. Cannot update system roles."""
        if db_obj.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system roles."
            )
        
        # Update basic fields (name, description)
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"permission_ids"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj) # Add to session if not already attached

        # Update permissions if provided (replace existing)
        if obj_in.permission_ids is not None: # Check for explicit list (even empty)
            await self.set_role_permissions(db, role_id=db_obj.id, permission_ids=obj_in.permission_ids)

        await db.commit()
        await db.refresh(db_obj, attribute_names=['permissions']) # Refresh to load updated permissions
        return db_obj

    async def set_role_permissions(
        self, db: AsyncSession, *, role_id: UUID, permission_ids: List[UUID]
    ) -> None:
        """Set the exact list of permissions for a role, removing old ones and adding new ones."""
        # 1. Remove existing permissions for this role
        delete_stmt = delete(role_permissions_table).where(
            role_permissions_table.c.role_id == role_id
        )
        await db.execute(delete_stmt)

        # 2. Add new permissions if any are provided
        if permission_ids:
            # TODO: Validate permission IDs exist?
            insert_values = [
                {"role_id": role_id, "permission_id": pid} for pid in permission_ids
            ]
            if insert_values:
                insert_stmt = insert(role_permissions_table).values(insert_values)
                try:
                    await db.execute(insert_stmt)
                except IntegrityError as e:
                    logger.error(f"Integrity error setting permissions for role {role_id}: {e}", exc_info=True)
                    await db.rollback() # Rollback this specific operation
                    # Raise a more specific error or handle as needed
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid permission ID provided.") from e
        # Commit happens in the calling function (create/update)

    async def delete_custom_role(self, db: AsyncSession, *, role_id: UUID, tenant_id: UUID) -> Optional[Role]:
        """Delete a custom role if it belongs to the tenant and is not a system role."""
        role = await self.get(db, record_id=role_id)
        if not role:
            return None # Not found
        if role.is_system_role:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system roles.")
        if role.tenant_id != tenant_id:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role does not belong to this tenant.")
        
        # Check if any users are assigned to this role in this tenant
        user_assigned = await self.check_role_assigned(db, role_id=role_id, tenant_id=tenant_id)
        if user_assigned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Cannot delete role with assigned users. Please reassign users first."
            )

        # Proceed with deletion (relationships should cascade if configured correctly)
        await db.delete(role)
        await db.commit()
        return role

    async def check_role_assigned(self, db: AsyncSession, *, role_id: UUID, tenant_id: UUID) -> bool:
        """Check if a role has any users assigned to it within a specific tenant."""
        stmt = select(exists().where(
            user_tenant_roles_table.c.role_id == role_id,
            user_tenant_roles_table.c.tenant_id == tenant_id
        ))
        result = await db.execute(stmt)
        return result.scalar_one()

    # --- User Role Assignments --- 

    async def get_users_for_role(self, db: AsyncSession, *, role_id: UUID, tenant_id: UUID) -> List[User]:
        """Get all users assigned to a specific role within a specific tenant."""
        stmt = (
            select(User)
            .join(user_tenant_roles_table, User.id == user_tenant_roles_table.c.user_id)
            .where(
                user_tenant_roles_table.c.role_id == role_id,
                user_tenant_roles_table.c.tenant_id == tenant_id
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def set_users_for_role(
        self, db: AsyncSession, *, role_id: UUID, tenant_id: UUID, user_ids: List[UUID]
    ) -> List[UUID]:
        """Set the exact list of users assigned to a role within a tenant.
        Removes users not in the list, adds users in the list.
        Returns the list of user IDs that were successfully assigned (or already existed).
        """
        # Validate role exists and belongs to tenant (or is system role)
        role = await self.get(db, record_id=role_id)
        if not role or (not role.is_system_role and role.tenant_id != tenant_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role {role_id} not found or not accessible in this tenant.")

        # 1. Remove existing assignments for this role in this tenant
        delete_stmt = delete(user_tenant_roles_table).where(
            user_tenant_roles_table.c.role_id == role_id,
            user_tenant_roles_table.c.tenant_id == tenant_id
        )
        await db.execute(delete_stmt)

        # 2. Add new assignments
        added_user_ids = []
        if user_ids:
            # Optional: Validate user IDs exist?
            insert_values = [
                {"user_id": uid, "role_id": role_id, "tenant_id": tenant_id}
                for uid in user_ids
            ]
            if insert_values:
                # Use bulk insert with do-nothing on conflict
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                insert_stmt = pg_insert(user_tenant_roles_table).values(insert_values)
                # Define conflict target based on the unique constraint
                conflict_target = ["user_id", "role_id", "tenant_id"]
                final_stmt = insert_stmt.on_conflict_do_nothing(index_elements=conflict_target)

                try:
                    await db.execute(final_stmt)
                    added_user_ids = user_ids # Assume all were added or existed if no error
                except IntegrityError as e:
                    # This might happen if a user_id doesn't exist (FK violation)
                    logger.error(f"Integrity error assigning users to role {role_id} in tenant {tenant_id}: {e}", exc_info=True)
                    await db.rollback()
                    # Raise a specific error indicating potential invalid user IDs
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, 
                        detail="One or more user IDs are invalid or could not be assigned."
                    ) from e
                except Exception as e:
                     logger.error(f"Unexpected error assigning users to role {role_id} in tenant {tenant_id}: {e}", exc_info=True)
                     await db.rollback()
                     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign users to role.") from e
        
        await db.commit()
        return added_user_ids # Return the list provided if successful

# Create a singleton instance
role_service = RoleService(Role)
