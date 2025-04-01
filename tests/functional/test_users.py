# Remove unused db_session import
# from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient  # Use AsyncClient
import pytest


# Test data
TEST_USER = {
    "email": f"pytest-user-{uuid4()}@virtualstack.example",  # Ensure unique email
    "password": "Password123!",
    "first_name": "Pytest",
    "last_name": "User",
}

# Mark tests as asyncio and remove skip
pytestmark = pytest.mark.asyncio

# Use async def and await, use authenticated_async_client


async def test_create_user(
    authenticated_async_client: AsyncClient,
):  # Use authenticated_async_client
    """Test creating a new user."""
    # Remove mock headers
    # Remove tenant_id from payload as it's not part of UserCreate schema
    user_data = TEST_USER  # Directly use TEST_USER

    response = await authenticated_async_client.post(  # Use await and add trailing slash
        "/api/v1/users/", json=user_data
    )
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["email"] == TEST_USER["email"]
    assert data["first_name"] == TEST_USER["first_name"]
    assert "id" in data
    assert "hashed_password" not in data  # Ensure password is not returned

    pytest.user_id = data["id"]  # Store user ID for subsequent tests
    # TODO: Consider using fixtures instead of sequential dependency via pytest.user_id


async def test_get_user_by_id(
    authenticated_async_client: AsyncClient,
):  # Use authenticated_async_client
    """Test getting a user by ID."""
    assert hasattr(pytest, "user_id"), "User ID not set from previous test"
    user_id = pytest.user_id
    # Remove mock headers

    response = await authenticated_async_client.get(f"/api/v1/users/{user_id}")  # Use await
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == TEST_USER["email"]


# TODO: Re-evaluate this test - '/me' endpoint requires the *calling* user, not a specific ID
# This test might need to use the authenticated_async_client without specifying a user_id
async def test_get_current_user_info(
    authenticated_async_client: AsyncClient,
):  # Use authenticated_async_client
    """Test getting current user info."""
    # Remove mock headers
    # This endpoint uses the token to find the user
    response = await authenticated_async_client.get("/api/v1/users/me")  # Use await
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert "id" in data
    # We can assert the ID matches the logged-in user if we retrieve it from the fixture/settings
    # For now, just check if ID exists


async def test_update_user(
    authenticated_async_client: AsyncClient,
):  # Use authenticated_async_client
    """Test updating a user."""
    assert hasattr(pytest, "user_id"), "User ID not set from previous test"
    user_id = pytest.user_id
    update_data = {"last_name": "User-Updated"}
    # Remove mock headers

    response = await authenticated_async_client.put(  # Use await
        f"/api/v1/users/{user_id}", json=update_data
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == user_id
    assert data["last_name"] == update_data["last_name"]
    # TODO: Add test for updating user's own info via /me endpoint


async def test_delete_user(
    authenticated_async_client: AsyncClient,
):  # Use authenticated_async_client
    """Test deleting a user."""
    assert hasattr(pytest, "user_id"), "User ID not set from previous test"
    user_id = pytest.user_id
    # Remove mock headers

    response = await authenticated_async_client.delete(f"/api/v1/users/{user_id}")  # Use await
    # Assert 204 No Content status code
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text

    # Verify it's gone
    response_get = await authenticated_async_client.get(f"/api/v1/users/{user_id}")  # Use await
    assert response_get.status_code == status.HTTP_404_NOT_FOUND
    # TODO: Add test for deleting user's own account via /me endpoint? (If applicable)
