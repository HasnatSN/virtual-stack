from typing import Any, Optional, Union

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.security import create_password_hash
from virtualstack.models.iam.user import User
from virtualstack.schemas.iam.user import UserCreate, UserUpdate
from virtualstack.services.base import CRUDBase


class UserService(CRUDBase[User, UserCreate, UserUpdate]):
    """Service for user management."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get a user by email."""
        stmt = select(self.model).where(self.model.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create a new user."""
        # TODO: Ensure password hashing is correctly implemented
        obj_in_data = jsonable_encoder(obj_in)
        password = obj_in_data.pop("password")
        # TODO: Validate password complexity requirements if needed
        obj_in_data["hashed_password"] = create_password_hash(password)

        db_obj = self.model(**obj_in_data)
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


user_service = UserService(User)
