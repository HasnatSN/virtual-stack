from typing import Any, List, Optional

from fastapi import APIRouter, Depends, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from virtualstack.api.deps import get_current_user
from virtualstack.core.exceptions import (
    http_not_found_error, 
    http_validation_error
)
from virtualstack.db.session import get_db
from virtualstack.models.iam.user import User
from virtualstack.schemas.iam.user import User as UserSchema, UserCreate, UserUpdate
from virtualstack.services.iam import user_service

router = APIRouter()


@router.get("/", response_model=List[UserSchema])
async def get_users(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
) -> Any:
    """
    Retrieve users.
    """
    users = await user_service.get_multi(db, skip=skip, limit=limit)
    return users


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Create a new user.
    """
    # Check if user with this email already exists
    existing_user = await user_service.get_by_email(db, email=user_in.email)
    if existing_user:
        raise http_validation_error(detail=f"User with email {user_in.email} already exists")
    
    # Create the user
    user = await user_service.create(db, obj_in=user_in)
    return user


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get current user information.
    """
    user = await user_service.get(db, id=UUID(current_user["id"]))
    if not user:
        raise http_not_found_error(detail="User not found")
    return user


@router.put("/me", response_model=UserSchema)
async def update_current_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Update current user information.
    """
    user = await user_service.get(db, id=UUID(current_user["id"]))
    if not user:
        raise http_not_found_error(detail="User not found")
    
    # Update the user
    user = await user_service.update(db, db_obj=user, obj_in=user_in)
    return user


@router.get("/{user_id}", response_model=UserSchema)
async def get_user_by_id(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Path(...),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get user by ID.
    """
    user = await user_service.get(db, id=user_id)
    if not user:
        raise http_not_found_error(detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Path(...),
    user_in: UserUpdate,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Update user information.
    """
    user = await user_service.get(db, id=user_id)
    if not user:
        raise http_not_found_error(detail="User not found")
    
    # Update the user
    user = await user_service.update(db, db_obj=user, obj_in=user_in)
    return user


@router.delete("/{user_id}", response_model=UserSchema, status_code=status.HTTP_200_OK)
async def delete_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Path(...),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Delete a user.
    """
    user = await user_service.get(db, id=user_id)
    if not user:
        raise http_not_found_error(detail="User not found")
    
    # Delete the user
    user = await user_service.delete(db, id=user_id)
    return user 