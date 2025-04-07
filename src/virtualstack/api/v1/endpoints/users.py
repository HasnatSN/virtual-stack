from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.api.deps import get_current_user, get_tenant_from_path, require_permission
from virtualstack.core.exceptions import http_not_found_error, http_validation_error
from virtualstack.db.session import get_db
from virtualstack.models.iam.user import User
from virtualstack.models.iam.tenant import Tenant
from virtualstack.schemas.iam.user import User as UserSchema
from virtualstack.schemas.iam.user import UserCreate, UserUpdate
from virtualstack.services.iam import user_service


router = APIRouter()


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(*, current_user: User = Depends(get_current_user)) -> UserSchema:
    """Get current authenticated user information."""
    return current_user


@router.put("/me", response_model=UserSchema)
async def update_current_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """Update current authenticated user information."""
    return await user_service.update(db, db_obj=current_user, obj_in=user_in)


# General TODOs for this file:
# - Clarify if /me endpoints belong here or elsewhere.
# - Add logging to /me endpoints.
