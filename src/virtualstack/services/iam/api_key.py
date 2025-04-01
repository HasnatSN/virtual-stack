from datetime import datetime
import hashlib
import secrets
from typing import Optional
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.models.iam.api_key import APIKey
from virtualstack.models.iam.user import User
from virtualstack.schemas.iam.api_key import APIKeyCreate, APIKeyUpdate
from virtualstack.services.base import CRUDBase


class APIKeyService(CRUDBase[APIKey, APIKeyCreate, APIKeyUpdate]):
    """Service for API key management."""

    async def create_with_user(
        self, db: AsyncSession, *, obj_in: APIKeyCreate, user_id: UUID
    ) -> tuple[APIKey, str]:
        """Create a new API key and return both the model and the full key value.

        Args:
            db: Database session
            obj_in: API key creation data
            user_id: User ID of the key owner

        Returns:
            A tuple containing (api_key_model, api_key_value)
        """
        obj_in_data = jsonable_encoder(obj_in)

        # Generate API key
        key_value = self._generate_api_key()
        key_prefix = key_value[:8]
        key_hash = self._hash_api_key(key_value)

        # Create database object
        db_obj = self.model(
            **obj_in_data, user_id=user_id, key_prefix=key_prefix, key_hash=key_hash
        )

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return db_obj, key_value

    async def get_by_prefix(self, db: AsyncSession, *, prefix: str) -> Optional[APIKey]:
        """Get an API key by its prefix.

        Args:
            db: Database session
            prefix: The API key prefix to search for

        Returns:
            The API key if found, None otherwise
        """
        stmt = select(self.model).where(self.model.key_prefix == prefix)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_multi_by_user(
        self, db: AsyncSession, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[APIKey]:
        """Get multiple API keys belonging to a user.

        Args:
            db: Database session
            user_id: User ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of API keys
        """
        stmt = select(self.model).where(self.model.user_id == user_id).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_multi_by_tenant(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[APIKey]:
        """Get multiple API keys scoped to a tenant.

        Args:
            db: Database session
            tenant_id: Tenant ID to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of API keys
        """
        stmt = select(self.model).where(self.model.tenant_id == tenant_id).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_last_used(self, db: AsyncSession, *, db_obj: APIKey) -> APIKey:
        """Update the last_used_at timestamp of an API key.

        Args:
            db: Database session
            db_obj: The API key object to update

        Returns:
            The updated API key
        """
        db_obj.last_used_at = datetime.utcnow()
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def validate_api_key(
        self, db: AsyncSession, *, api_key: str
    ) -> Optional[tuple[APIKey, User]]:
        """Validate an API key and return the associated key and user if valid.

        Args:
            db: Database session
            api_key: The API key to validate

        Returns:
            A tuple of (api_key, user) if valid, None otherwise
        """
        if not api_key or len(api_key) < 8:
            return None

        key_prefix = api_key[:8]
        key_hash = self._hash_api_key(api_key)

        # Get the API key by prefix
        stmt = select(self.model).where(
            and_(
                self.model.key_prefix == key_prefix,
                self.model.key_hash == key_hash,
                self.model.is_active,
            )
        )
        result = await db.execute(stmt)
        db_obj = result.scalars().first()

        if not db_obj:
            return None

        # Check if expired
        if db_obj.expires_at and db_obj.expires_at < datetime.utcnow():
            return None

        # Get the associated user
        user_stmt = select(User).where(User.id == db_obj.user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalars().first()

        if not user or not user.is_active:
            return None

        # Update the last used timestamp
        await self.update_last_used(db, db_obj=db_obj)

        return db_obj, user

    def _generate_api_key(self) -> str:
        """Generate a new random API key.

        Returns:
            A string containing the API key
        """
        # Generate a 32-byte random token
        token = secrets.token_hex(32)
        return f"vs_{token}"

    def _hash_api_key(self, key: str) -> str:
        """Hash an API key for secure storage.

        Args:
            key: The API key to hash

        Returns:
            The hashed API key
        """
        return hashlib.sha256(key.encode()).hexdigest()


# Create a singleton instance
api_key_service = APIKeyService(APIKey)
