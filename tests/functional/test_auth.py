import pytest
from httpx import AsyncClient
from fastapi import status

from virtualstack.core.config import settings

# TODO: Add tests for token validation/expiry


@pytest.mark.asyncio # Mark as async test
async def test_login(async_client: AsyncClient): # Add async
    """Test login endpoint with JSON payload."""
    login_data = {
        "email": settings.TEST_USER_EMAIL,
        "password": settings.TEST_USER_PASSWORD,
    }
    response = await async_client.post("/api/v1/auth/login", json=login_data) # Add await
    assert response.status_code == status.HTTP_200_OK, f"Failed with response: {response.text}"
    token = response.json()
    assert "access_token" in token
    assert token["token_type"] == "bearer"


@pytest.mark.asyncio # Mark as async test
async def test_login_access_token(async_client: AsyncClient): # Add async
    """Test OAuth2 compatible login endpoint."""
    login_data = {
        "username": settings.TEST_USER_EMAIL,
        "password": settings.TEST_USER_PASSWORD,
    }
    response = await async_client.post( # Add await
        "/api/v1/auth/login/access-token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == status.HTTP_200_OK, f"Failed with response: {response.text}"
    token = response.json()
    assert "access_token" in token
    assert token["token_type"] == "bearer"


@pytest.mark.asyncio # Mark as async test
async def test_login_invalid_credentials(async_client: AsyncClient): # Add async
    """Test login with invalid credentials."""
    login_data = {"email": settings.TEST_USER_EMAIL, "password": "wrongpassword"}
    response = await async_client.post("/api/v1/auth/login", json=login_data) # Add await
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]
