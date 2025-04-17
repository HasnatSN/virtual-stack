from datetime import timedelta
from typing import Any
import logging

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

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiting function factory
# _rate_limit_dependency = rate_limit(max_requests=5, window_seconds=60) # Temporarily disable

# TODO: Ensure this endpoint fully matches OAuth2 spec if needed later.
# TODO: Consider adding refresh token logic.
@router.post(
    "/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    # dependencies=[Depends(_rate_limit_dependency)] # Temporarily disable
)
async def login_access_token(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """OAuth2 compatible token login, get an access token for future requests.
    Uses username from the form data as email.
    """
    logger.info(f"Attempting login for user: {form_data.username}")
    user = await user_service.get_by_email(db, email=form_data.username)
    
    if not user:
        logger.warning(f"Login failed: User not found for email {form_data.username}")
        raise http_authentication_error(detail="Incorrect email or password")
    
    logger.debug(f"Login attempt: User found (ID: {user.id}). Verifying password...")
    is_password_valid = verify_password(form_data.password, user.hashed_password)
    
    if not is_password_valid:
        logger.warning(f"Login failed: Invalid password for user {form_data.username} (ID: {user.id})")
        raise http_authentication_error(detail="Incorrect email or password")
    
    logger.debug(f"Login attempt: Password verified for user {user.id}. Checking active status...")
    if not user.is_active:
        logger.warning(f"Login failed: User {user.id} is inactive.")
        raise http_authentication_error(detail="Inactive user")

    logger.info(f"Login successful for user {user.id}. Creating token...")
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
