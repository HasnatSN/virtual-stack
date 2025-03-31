import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

# Test data
TEST_USER = {
    "email": f"pytest-user-{uuid4()}@virtualstack.example", # Ensure unique email
    "password": "Password123!",
    "first_name": "Pytest",
    "last_name": "User"
}

# We need authenticated client and tenant_id for these tests
# TODO: Create fixtures for authenticated client and pre-created tenant
pytestmark = pytest.mark.skip(reason="Requires authenticated client and tenant fixtures")

def test_create_user(client: TestClient, db_session: AsyncSession):
    """Test creating a new user."""
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    # Assume tenant_id is available via a fixture later
    tenant_id = getattr(pytest, 'tenant_id', None) 
    assert tenant_id is not None, "Tenant ID fixture needed"
    
    user_data = {**TEST_USER, "tenant_id": str(tenant_id)}

    response = client.post(
        "/api/v1/users", # Missing trailing slash?
        json=user_data,
        headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["email"] == TEST_USER["email"]
    assert data["first_name"] == TEST_USER["first_name"]
    assert "id" in data
    assert "hashed_password" not in data # Ensure password is not returned
    
    pytest.user_id = data["id"]


def test_get_user_by_id(client: TestClient, db_session: AsyncSession):
    """Test getting a user by ID."""
    assert hasattr(pytest, "user_id"), "User ID not set from previous test"
    user_id = pytest.user_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}

    response = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == TEST_USER["email"]


def test_get_current_user_info(client: TestClient, db_session: AsyncSession):
    """Test getting current user info."""
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    # This endpoint uses the token to find the user, currently mocked
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert "id" in data
    # Cannot assert specific user ID due to mock


def test_update_user(client: TestClient, db_session: AsyncSession):
    """Test updating a user."""
    assert hasattr(pytest, "user_id"), "User ID not set from previous test"
    user_id = pytest.user_id
    update_data = {"last_name": "User-Updated"}
    headers = {"Authorization": "Bearer MOCK_TOKEN"}

    response = client.put(
        f"/api/v1/users/{user_id}", 
        json=update_data,
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == user_id
    assert data["last_name"] == update_data["last_name"]


def test_delete_user(client: TestClient, db_session: AsyncSession):
    """Test deleting a user."""
    assert hasattr(pytest, "user_id"), "User ID not set from previous test"
    user_id = pytest.user_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}

    response = client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text

    # Verify it's gone
    response_get = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert response_get.status_code == status.HTTP_404_NOT_FOUND 