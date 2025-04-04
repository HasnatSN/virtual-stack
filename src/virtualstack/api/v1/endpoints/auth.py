from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.config import settings
from virtualstack.core.exceptions import http_authentication_error
from virtualstack.core.rate_limiter import rate_limit
from virtualstack.core.security import create_access_token, verify_password
from virtualstack.db.session import get_db
from virtualstack.schemas.iam.auth import LoginRequest, Token
from virtualstack.services.iam import user_service


router = APIRouter()


# Rate limiting for authentication endpoints - 5 requests per minute
login_rate_limiter = rate_limit(max_requests=5, window_seconds=60)


@router.post("/login/access-token", response_model=Token, status_code=status.HTTP_200_OK)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    _: bool = Depends(login_rate_limiter),
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests.
    Uses username from the form data as email.
    """
    user = await user_service.get_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise http_authentication_error(detail="Incorrect email or password")
    if not user.is_active:
        raise http_authentication_error(detail="Inactive user")

    # Create access token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


# TODO: Add a /token endpoint to match the front-end MVP requirements
@router.post("/token", response_model=Token, status_code=status.HTTP_200_OK)
async def get_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    _: bool = Depends(login_rate_limiter),
) -> Any:
    """OAuth2 compatible token endpoint (alias for login_access_token).
    This endpoint matches the frontend MVP requirements.
    """
    return await login_access_token(db=db, form_data=form_data, _=_)


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(login_rate_limiter),
) -> Any:
    """Login with email and password."""
    user = await user_service.get_by_email(db, email=login_data.email)
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise http_authentication_error(detail="Incorrect email or password")
    if not user.is_active:
        raise http_authentication_error(detail="Inactive user")

    # Create access token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
