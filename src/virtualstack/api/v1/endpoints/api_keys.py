import logging
from typing import Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import (
    get_current_active_user,
)
from virtualstack.db.session import get_db
from virtualstack.models.iam import User
from virtualstack.schemas.iam.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyUpdate,
    APIKeyWithValue,
)
from virtualstack.services.iam import api_key_service

# TODO: Configure logging properly
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=APIKeyWithValue, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    api_key_in: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
) -> APIKeyWithValue:
    """Create a new API key.

    - If a tenant ID is provided, validates that the user has access to that tenant
    - Returns the full API key value which will not be available again
    """
    # Check if tenant scoped and user has access to the tenant
    if api_key_in.tenant_id and not current_user.is_superuser:
        # In a real application, we would check if the user has access to the tenant
        # For now, we just deny non-superusers from creating tenant-scoped keys arbitrarily
        # TODO: Implement proper tenant access check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot create API keys for this tenant.",
        )

    # Proceed with creation if checks pass
    try:
        # Create the API key
        db_obj, key_value = await api_key_service.create_with_user(
            db=db,
            obj_in=api_key_in,
            user_id=current_user.id,
            tenant_id=api_key_in.tenant_id # Pass tenant_id explicitly if provided
        )

        # Ensure db_obj is not None (should be handled by service exception if fetch failed)
        if db_obj is None:
             raise HTTPException(status_code=500, detail="Failed to retrieve created API key object.")

        # Manually construct dictionary from the ORM object
        # This helps ensure all fields, including server defaults like created_at,
        # are available before Pydantic validation.
        response_data = {
            "id": db_obj.id,
            "name": db_obj.name,
            "key_prefix": db_obj.key_prefix,
            "description": db_obj.description,
            "is_active": db_obj.is_active,
            "expires_at": db_obj.expires_at,
            "last_used_at": db_obj.last_used_at,
            "user_id": db_obj.user_id,
            "tenant_id": db_obj.tenant_id,
            "created_at": db_obj.created_at,
            "updated_at": db_obj.updated_at,
            "scope": db_obj.scope,
            "key": key_value # Add the raw key
        }
        
        # Now validate the dictionary using the response model
        return APIKeyWithValue.model_validate(response_data)

    except ValueError as ve: # Catch tenant_id validation error from service
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        # Log the full error for debugging
        logger.exception("Error creating API key endpoint") # Assuming logger is configured
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: An unexpected error occurred.",
        )

    # response = APIKeyWithValue.model_validate(db_obj) # OLD - Caused validation error
    # response.key = key_value # OLD - Too late



@router.get("/", response_model=list[APIKey])
async def read_api_keys(
    *,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
) -> list[APIKey]:
    """Retrieve API keys.

    - Regular users can only see their own API keys
    - Superusers can see all API keys
    - Can filter by tenant_id
    """
    if current_user.is_superuser:
        if tenant_id:
            api_keys = await api_key_service.get_multi_by_tenant(
                db=db, tenant_id=tenant_id, skip=skip, limit=limit
            )
        else:
            api_keys = await api_key_service.get_multi(db=db, skip=skip, limit=limit)
    else:
        api_keys = await api_key_service.get_multi_by_user(
            db=db, user_id=current_user.id, skip=skip, limit=limit
        )

        # Filter by tenant_id if requested
        if tenant_id:
            api_keys = [key for key in api_keys if key.tenant_id == tenant_id]

    return api_keys


@router.get("/{api_key_id}", response_model=APIKey)
async def read_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    api_key_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> APIKey:
    """Get a specific API key by ID.

    - Regular users can only access their own API keys
    - Superusers can access any API key
    """
    api_key = await api_key_service.get(db=db, record_id=api_key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Check permissions
    if not current_user.is_superuser and api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this API key",
        )

    return api_key


@router.put("/{api_key_id}", response_model=APIKey)
async def update_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    api_key_id: UUID,
    api_key_in: APIKeyUpdate,
    current_user: User = Depends(get_current_active_user),
) -> APIKey:
    """Update an API key.

    - Regular users can only update their own API keys
    - Superusers can update any API key
    """
    api_key = await api_key_service.get(db=db, record_id=api_key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Check permissions
    if not current_user.is_superuser and api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this API key",
        )

    return await api_key_service.update(
        db=db,
        db_obj=api_key,
        obj_in=api_key_in,
    )



@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    api_key_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete an API key.

    - Regular users can only delete their own API keys
    - Superusers can delete any API key
    """
    api_key = await api_key_service.get(db=db, record_id=api_key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Check permissions
    if not current_user.is_superuser and api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this API key",
        )

    deleted_key = await api_key_service.delete(db=db, record_id=api_key_id)
    if not deleted_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or already deleted",
        )
    return None
