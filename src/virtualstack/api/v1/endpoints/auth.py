from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from virtualstack.core.config import settings
from virtualstack.core.exceptions import http_authentication_error
from virtualstack.core.security import create_access_token
from virtualstack.core.rate_limiter import rate_limit
from virtualstack.db.session import get_db
from virtualstack.schemas.iam.auth import Token, LoginRequest
from virtualstack.services.iam import user_service


router = APIRouter()


# Rate limiting for authentication endpoints - 5 requests per minute
login_rate_limiter = rate_limit(max_requests=5, window_seconds=60)


@router.post("/login/access-token", response_model=Token, status_code=status.HTTP_200_OK)
async def login_access_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    _: bool = Depends(login_rate_limiter)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    # For demo purposes, return a mock token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            subject="123e4567-e89b-12d3-a456-426614174000", 
            expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(login_rate_limiter)
) -> Any:
    """
    Login with email and password.
    """
    # For demo purposes, return a mock token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            subject="123e4567-e89b-12d3-a456-426614174000", 
            expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    } 