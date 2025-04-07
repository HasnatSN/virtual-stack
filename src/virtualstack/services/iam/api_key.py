from datetime import datetime, timezone, timedelta
import hashlib
import secrets
from typing import Optional, Tuple, List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, select, inspect
from sqlalchemy.orm import load_only

from virtualstack.models.iam.api_key import APIKey
from virtualstack.models.iam.user import User
from virtualstack.schemas.iam.api_key import APIKeyCreate, APIKeyUpdate, APIKeyScope
from virtualstack.services.base import CRUDBase

# Setup logger
import logging
logger = logging.getLogger(__name__)


class APIKeyService(CRUDBase[APIKey, APIKeyCreate, APIKeyUpdate]):
    """Service for API key management."""

    # --- Helper Methods for Key Generation/Hashing ---
    def _generate_api_key(self, length: int = 32) -> str:
        """Generate a secure random API key with a prefix."""
        # VSAK = Virtual Stack API Key prefix
        return f"vsak_{secrets.token_urlsafe(length)}"

    def _hash_api_key(self, key_value: str) -> str:
        """Hash the API key using SHA256 for storage."""
        return hashlib.sha256(key_value.encode()).hexdigest()
    # --- End Helper Methods ---

    async def create_with_user(
        self, db: AsyncSession, *, obj_in: APIKeyCreate, user_id: UUID, tenant_id: Optional[UUID] = None
    ) -> tuple[APIKey, str]:
        """Creates an API key, hashes it, and associates it with a user and optionally a tenant."""
        # Generate the raw key value using the internal helper method
        raw_key = self._generate_api_key()
        key_prefix = raw_key[:8]  # Use first 8 characters as prefix
        # Hash the key using the internal helper method
        key_hash = self._hash_api_key(raw_key)

        # Prepare the database object attributes
        db_obj_data = {
            "name": obj_in.name,
            "key_prefix": key_prefix,
            "key_hash": key_hash,
            "description": obj_in.description,
            "is_active": obj_in.is_active,
            "user_id": user_id,
            "scope": obj_in.scope,
        }

        # Handle tenant_id based on scope
        if obj_in.scope == APIKeyScope.TENANT:
            if tenant_id is None:
                # If the function wasn't passed a tenant_id but scope is TENANT,
                # try getting it from the schema (though typically it should come via context)
                tenant_id = obj_in.tenant_id
            if tenant_id is None:
                 # TODO: This should ideally be caught by validation earlier
                raise ValueError("tenant_id is required for tenant-scoped API keys")
            db_obj_data["tenant_id"] = tenant_id
        elif obj_in.scope == APIKeyScope.GLOBAL:
            db_obj_data["tenant_id"] = None # Explicitly set to None for GLOBAL scope

        # Handle expires_at: Store timezone-aware UTC
        if obj_in.expires_at:
            # Ensure it's UTC and keep it timezone-aware
            expires_at_aware_utc = obj_in.expires_at.astimezone(timezone.utc) # Keep it timezone-aware
            db_obj_data["expires_at"] = expires_at_aware_utc
        else:
            db_obj_data["expires_at"] = None # Explicitly set to None if not provided

        # Create the database object directly with the prepared attributes
        db_obj = self.model(**db_obj_data)

        try:
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj) # Ensure refresh is after commit

            # Log the creation event
            logger.info(f"API key {db_obj.id} created successfully.")

            # Explicitly re-fetch the object after commit to ensure server defaults (like created_at) are loaded
            created_db_obj = await db.get(self.model, db_obj.id) 
            if not created_db_obj:
                # This should ideally not happen if commit succeeded
                logger.error(f"Failed to fetch API key {db_obj.id} immediately after creation.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve created API key."
                )
            # TODO: Add explicit refresh to ensure server defaults are loaded onto the instance
            await db.refresh(created_db_obj) # Ensure all attributes are loaded, including server_default
            # Return the re-fetched DB object and the raw key value
            return created_db_obj, raw_key
        except IntegrityError as e:
            await db.rollback()
            # Log the error for debugging
            logger.error(f"Failed to create API key due to IntegrityError: {e}", exc_info=True)
            # Raise a more specific or user-friendly exception if needed
            # For now, re-raising or wrapping might be appropriate
            # Consider specific handling for duplicate names or other constraints
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create API key: {e}" # TODO: Improve error detail for user
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"An unexpected error occurred creating API key: {e}", exc_info=True)
            raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail=f"An unexpected error occurred: {e}" # TODO: Improve error detail for user
            )

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
    ) -> List[APIKey]:
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
        keys = result.scalars().all()
        # TODO: Consider if refresh is truly needed or if eager loading options solve it
        refreshed_keys = []
        for key in keys:
            try:
                await db.refresh(key) # Refresh to load potential defaults/latest state
                refreshed_keys.append(key)
            except Exception as e:
                logger.error(f"Failed to refresh API key {key.id} for user {user_id} in service get_multi_by_user: {e}")
                # Include potentially unrefreshed keys
                refreshed_keys.append(key)
        return refreshed_keys

    async def get_multi_by_tenant(
        self, db: AsyncSession, *, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[APIKey]:
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
        keys = result.scalars().all()
        # TODO: Consider if refresh is truly needed or if eager loading options solve it
        refreshed_keys = []
        for key in keys:
            try:
                await db.refresh(key) # Refresh to load potential defaults/latest state
                refreshed_keys.append(key)
            except Exception as e:
                logger.error(f"Failed to refresh API key {key.id} for tenant {tenant_id} in service get_multi_by_tenant: {e}")
                # Include potentially unrefreshed keys
                refreshed_keys.append(key)
        return refreshed_keys

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[APIKey]:
        """Retrieve multiple API keys."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await db.execute(stmt)
        keys = result.scalars().all()
        # TODO: Consider if refresh is truly needed or if eager loading options solve it
        refreshed_keys = []
        for key in keys:
            try:
                await db.refresh(key) # Refresh to load potential defaults/latest state
                refreshed_keys.append(key)
            except Exception as e:
                logger.error(f"Failed to refresh API key {key.id} in service get_multi: {e}")
                # Include potentially unrefreshed keys to see if Pydantic still fails
                refreshed_keys.append(key)
        return refreshed_keys

    async def update_last_used(self, db: AsyncSession, *, db_obj: APIKey) -> APIKey:
        """Update the last_used_at timestamp of an API key.

        Args:
            db: Database session
            db_obj: The API key object to update

        Returns:
            The updated API key
        """
        db_obj.last_used_at = datetime.now(timezone.utc)
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
        # Use naive UTC datetime for comparison, as DB read seems consistently naive
        now_naive_utc = datetime.utcnow()
        if db_obj.expires_at:
            # ADDED: Log the retrieved expires_at value and type
            logger.debug(f"Retrieved expires_at for key {db_obj.id}: {db_obj.expires_at} (Type: {type(db_obj.expires_at)})")
            # Compare naive db time with naive current time
            if db_obj.expires_at < now_naive_utc:
                logger.warning(f"API key {db_obj.id} validation failed: Expired. {db_obj.expires_at} < {now_naive_utc}")
                logger.warning("--> Expiry check returning None.")
                return None # Key is expired

        # If key is valid and not expired, update last_used_at
        db_obj.last_used_at = datetime.now(timezone.utc) # Still use aware for writing
        db.add(db_obj)
        # We don't commit here; rely on the calling context (e.g., dependency) to handle commit/rollback
        # await db.commit() # REMOVED - Let caller manage transaction
        # await db.refresh(db_obj) # REMOVED - last_used_at update doesn't need immediate refresh

        # Get associated user
        # user = await db.get(User, db_obj.user_id) # This might require options(selectinload(User))
        # Optimized: Load user relationship if not already loaded
        if 'user' not in db_obj.__dict__:
             await db.refresh(db_obj, attribute_names=['user'])

        if not db_obj.user:
             logger.error(f"API key {db_obj.id} is missing associated user {db_obj.user_id}")
             return None

        return db_obj, db_obj.user # Return tuple (APIKey, User)


# Create a singleton instance
api_key_service = APIKeyService(APIKey)
