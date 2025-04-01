from typing import Any, Generic, Optional, TypeVar, Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.db.base_class import Base


ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base class for CRUD operations."""

    def __init__(self, model: type[ModelType]):
        """Initialize with the SQLAlchemy model class."""
        self.model = model

    async def get(self, db: AsyncSession, *, record_id: UUID) -> Optional[ModelType]:
        """Get a single record by ID."""
        query = select(self.model).where(self.model.id == record_id)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> list[ModelType]:
        """Get multiple records."""
        query = select(self.model).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, dict[str, Any]],
    ) -> ModelType:
        """Update a record."""
        obj_data = jsonable_encoder(db_obj)
        # Use model_dump for Pydantic V2 compatibility
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, record_id: UUID) -> Optional[ModelType]:
        """Delete a record by ID."""
        db_obj = await self.get(db, record_id=record_id)
        if not db_obj:
            return None

        # Hard delete for now - no soft delete support
        await db.delete(db_obj)
        await db.commit()
        return db_obj

    async def count(self, db: AsyncSession) -> int:
        """Count total records."""
        query = select(self.model)

        # Add soft delete filter if applicable
        if hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        result = await db.execute(query)
        return len(result.scalars().all())
