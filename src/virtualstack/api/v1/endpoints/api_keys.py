from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import (
    get_current_active_user,
    get_current_superuser,
    require_permission,
)
from virtualstack.core.permissions import Permission
from virtualstack.db.session import get_db
from virtualstack.models.iam import User
from virtualstack.schemas.iam.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeyUpdate,
    APIKeyWithValue,
)
from virtualstack.services.iam.api_key import api_key_service


router = APIRouter()


@router.post("/", response_model=APIKeyWithValue, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    api_key_in: APIKeyCreate,
    current_user: Dict = Depends(get_current_active_user),
) -> APIKeyWithValue:
    """
    Create a new API key.
    
    - If a tenant ID is provided, validates that the user has access to that tenant
    - Returns the full API key value which will not be available again
    """
    # Check if tenant scoped and user has access to the tenant
    if api_key_in.tenant_id:
        # In a real application, we would check if the user has access to the tenant
        # For now, we'll just allow it if the user is a superuser
        if not current_user.get("is_superuser"):
            # Check if user belongs to this tenant
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create API keys for this tenant",
            )
    
    # Create the API key
    db_obj, key_value = await api_key_service.create_with_user(
        db=db,
        obj_in=api_key_in,
        user_id=UUID(current_user["id"]),
    )
    
    # Convert to response model and add the key value
    response = APIKeyWithValue.model_validate(db_obj)
    response.key = key_value
    
    return response


@router.get("/", response_model=List[APIKey])
async def read_api_keys(
    *,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    tenant_id: Optional[UUID] = None,
    current_user: Dict = Depends(get_current_active_user),
) -> List[APIKey]:
    """
    Retrieve API keys.
    
    - Regular users can only see their own API keys
    - Superusers can see all API keys
    - Can filter by tenant_id
    """
    if current_user.get("is_superuser"):
        if tenant_id:
            api_keys = await api_key_service.get_multi_by_tenant(
                db=db, tenant_id=tenant_id, skip=skip, limit=limit
            )
        else:
            api_keys = await api_key_service.get_multi(db=db, skip=skip, limit=limit)
    else:
        api_keys = await api_key_service.get_multi_by_user(
            db=db, user_id=UUID(current_user["id"]), skip=skip, limit=limit
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
    current_user: Dict = Depends(get_current_active_user),
) -> APIKey:
    """
    Get a specific API key by ID.
    
    - Regular users can only access their own API keys
    - Superusers can access any API key
    """
    api_key = await api_key_service.get(db=db, id=api_key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    # Check permissions
    if not current_user.get("is_superuser") and str(api_key.user_id) != current_user["id"]:
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
    current_user: Dict = Depends(get_current_active_user),
) -> APIKey:
    """
    Update an API key.
    
    - Regular users can only update their own API keys
    - Superusers can update any API key
    """
    api_key = await api_key_service.get(db=db, id=api_key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    # Check permissions
    if not current_user.get("is_superuser") and str(api_key.user_id) != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this API key",
        )
    
    api_key = await api_key_service.update(
        db=db,
        db_obj=api_key,
        obj_in=api_key_in,
    )
    
    return api_key


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    api_key_id: UUID,
    current_user: Dict = Depends(get_current_active_user),
) -> None:
    """
    Delete an API key.
    
    - Regular users can only delete their own API keys
    - Superusers can delete any API key
    """
    api_key = await api_key_service.get(db=db, id=api_key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    # Check permissions
    if not current_user.get("is_superuser") and str(api_key.user_id) != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this API key",
        )
    
    await api_key_service.remove(db=db, id=api_key_id) 