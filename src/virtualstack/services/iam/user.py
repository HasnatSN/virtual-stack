from typing import Optional, Any, Dict, Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.models.iam.user import User
from virtualstack.schemas.iam.user import UserCreate, UserUpdate
from virtualstack.services.base import CRUDBase


class UserService(CRUDBase[User, UserCreate, UserUpdate]):
    """
    Service for user management.
    """
    
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """
        Get a user by email.
        """
        stmt = select(self.model).where(self.model.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()
    
    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """
        Create a new user.
        """
        # In a real application, we would hash the password here
        # For demonstration purposes, we'll store it as-is
        obj_in_data = jsonable_encoder(obj_in)
        password = obj_in_data.pop("password")
        obj_in_data["hashed_password"] = password  # In real app: get_password_hash(password)
        
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        """
        Update a user.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
            
        if update_data.get("password"):
            # In a real application, we would hash the password here
            # For demonstration purposes, we'll store it as-is
            hashed_password = update_data.pop("password")  # In real app: get_password_hash(password)
            update_data["hashed_password"] = hashed_password
            
        return await super().update(db, db_obj=db_obj, obj_in=update_data)


user_service = UserService(User) 