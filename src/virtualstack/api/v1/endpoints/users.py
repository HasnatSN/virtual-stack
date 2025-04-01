from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import get_current_user
from virtualstack.core.exceptions import http_not_found_error, http_validation_error
from virtualstack.db.session import get_db
from virtualstack.models.iam.user import User
from virtualstack.schemas.iam.user import User as UserSchema
from virtualstack.schemas.iam.user import UserCreate, UserUpdate
from virtualstack.services.iam import user_service


router = APIRouter()


@router.get("/", response_model=list[UserSchema])
async def get_users(
    *,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> Any:
    """Retrieve users."""
    return await user_service.get_multi(db, skip=skip, limit=limit)


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """Create a new user."""
    # Check if user with this email already exists
    existing_user = await user_service.get_by_email(db, email=user_in.email)
    if existing_user:
        raise http_validation_error(detail=f"User with email {user_in.email} already exists")

    # Create the user
    return await user_service.create(db, obj_in=user_in)


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(*, current_user: User = Depends(get_current_user)) -> UserSchema:
    """Get current user information."""
    return current_user


@router.put("/me", response_model=UserSchema)
async def update_current_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Update current user information."""
    user = await user_service.get(db, id=UUID(current_user["id"]))
    if not user:
        raise http_not_found_error(detail="User not found")

    # Update the user
    return await user_service.update(db, db_obj=user, obj_in=user_in)


@router.get("/{user_id}", response_model=UserSchema)
async def get_user_by_id(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Path(...),
) -> Any:
    """Get user by ID."""
    user = await user_service.get(db, record_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Path(...),
    user_in: UserUpdate,
) -> Any:
    """Update user information."""
    user = await user_service.get(db, record_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update the user
    updated_user = await user_service.update(db, db_obj=user, obj_in=user_in)
    return updated_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a user."""
    user = await user_service.get(db, record_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check permissions (assuming only superusers can delete others for now)
    # TODO: Refine permission check (e.g., tenant admins?)
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to delete this user",
        )

    deleted_user = await user_service.delete(db, record_id=user_id)
    if not deleted_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or already deleted",
        )
    return None


# TODO: Add tests for get/update /me endpoints using authenticated client
# TODO: Implement proper authorization checks for all user endpoints
