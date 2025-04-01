from uuid import uuid4

from fastapi import status
from httpx import AsyncClient
import pytest

from virtualstack.schemas.iam.api_key import APIKeyScope


# Test data
TEST_API_KEY_BASE_NAME = f"pytest-key-{uuid4()}"
TEST_API_KEY = {
    "name": TEST_API_KEY_BASE_NAME,
    "description": "API Key created via pytest",
    "scope": APIKeyScope.GLOBAL.value,
}

# Mark tests as asyncio and remove skip
pytestmark = pytest.mark.asyncio

# Use async def and await, use authenticated_async_client


async def test_create_api_key(authenticated_async_client: AsyncClient):
    """Test creating a new API key."""
    response = await authenticated_async_client.post("/api/v1/api-keys/", json=TEST_API_KEY)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["name"] == TEST_API_KEY["name"]
    assert data["description"] == TEST_API_KEY["description"]
    assert data["scope"] == TEST_API_KEY["scope"]
    assert "id" in data
    assert "key_prefix" in data
    assert "key" in data
    assert len(data["key"]) > 10
    assert data["key"].startswith("vs_")

    pytest.api_key_id = data["id"]
    pytest.api_key_prefix = data["key_prefix"]


async def test_get_api_keys(authenticated_async_client: AsyncClient):
    """Test retrieving API keys (should retrieve the one created)."""
    response = await authenticated_async_client.get("/api/v1/api-keys/")
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert isinstance(data, list)
    found = any(item["id"] == pytest.api_key_id for item in data if "id" in item)
    assert (
        found
    ), f"Created API key ID {getattr(pytest, 'api_key_id', 'N/A')} not found in list: {data}"


async def test_get_api_key_by_id(authenticated_async_client: AsyncClient):
    """Test getting a specific API key by ID."""
    assert hasattr(pytest, "api_key_id"), "API Key ID not set from previous test"
    api_key_id = pytest.api_key_id

    response = await authenticated_async_client.get(f"/api/v1/api-keys/{api_key_id}")
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == api_key_id
    assert data["name"] == TEST_API_KEY["name"]
    assert data["scope"] == TEST_API_KEY["scope"]


async def test_update_api_key(authenticated_async_client: AsyncClient):
    """Test updating an API key."""
    assert hasattr(pytest, "api_key_id"), "API Key ID not set from previous test"
    api_key_id = pytest.api_key_id
    update_data = {"description": "Updated via pytest"}

    response = await authenticated_async_client.put(
        f"/api/v1/api-keys/{api_key_id}", json=update_data
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == api_key_id
    assert data["description"] == update_data["description"]


async def test_delete_api_key(authenticated_async_client: AsyncClient):
    """Test deleting an API key."""
    assert hasattr(pytest, "api_key_id"), "API Key ID not set from previous test"
    api_key_id = pytest.api_key_id

    response = await authenticated_async_client.delete(f"/api/v1/api-keys/{api_key_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text

    response_get = await authenticated_async_client.get(f"/api/v1/api-keys/{api_key_id}")
    assert response_get.status_code == status.HTTP_404_NOT_FOUND
