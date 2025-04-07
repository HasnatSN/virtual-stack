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
# TODO: Maybe use a more specific schema than Token if frontend needs more user info directly on login?
from virtualstack.schemas.iam.auth import Token  # Removed LoginRequest as it's no longer used
from virtualstack.services.iam import user_service


router = APIRouter()


# Rate limiting for authentication endpoints - 5 requests per minute
login_rate_limiter = rate_limit(max_requests=5, window_seconds=60)


# TODO: Ensure this endpoint fully matches OAuth2 spec if needed later.
# TODO: Consider adding refresh token logic.
@router.post("/token", response_model=Token, status_code=status.HTTP_200_OK)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    _: bool = Depends(login_rate_limiter),
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests.
    Uses username from the form data as email.
    """
    # TODO: Log failed login attempts for security monitoring.
    user = await user_service.get_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        # TODO: Add specific error code for invalid credentials?
        raise http_authentication_error(detail="Incorrect email or password")
    if not user.is_active:
        # TODO: Add specific error code for inactive user?
        raise http_authentication_error(detail="Inactive user")

    # Create access token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    # TODO: Add user roles/permissions or tenant info to the token payload if needed client-side?
    return {
        "access_token": create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


# Removed redundant /login endpoint (using LoginRequest schema).
# The /auth/token endpoint above uses the standard OAuth2PasswordRequestForm flow.
