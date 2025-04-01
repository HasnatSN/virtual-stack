# Remove unused db_session import if it's not used elsewhere after removing from params
# from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient  # Import AsyncClient
import pytest


# Test data
TEST_TENANT_NAME = f"pytest-tenant-{uuid4()}"
TEST_TENANT_SLUG = TEST_TENANT_NAME  # Use name as slug, fits the pattern
TEST_TENANT_DATA = {
    "name": TEST_TENANT_NAME,
    "slug": TEST_TENANT_SLUG,  # TODO: Verify if slug generation logic should be different in production
    "description": "Tenant created via pytest",
}

# Mark tests as asyncio
pytestmark = pytest.mark.asyncio

# Use async def and await, use authenticated_async_client


async def test_create_tenant(authenticated_async_client: AsyncClient):
    """Test creating a new tenant using an authenticated async client."""
    response = await authenticated_async_client.post("/api/v1/tenants/", json=TEST_TENANT_DATA)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["name"] == TEST_TENANT_DATA["name"]
    assert "id" in data
    pytest.tenant_id = data["id"]  # Store tenant ID for subsequent tests


async def test_get_tenants(authenticated_async_client: AsyncClient):
    """Test retrieving tenants (should include the one created)."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from previous test"

    response = await authenticated_async_client.get("/api/v1/tenants/")
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert isinstance(data, list)
    found = any(item["id"] == pytest.tenant_id for item in data)
    assert found, "Created tenant not found in list"


async def test_get_tenant_by_id(authenticated_async_client: AsyncClient):
    """Test getting a specific tenant by ID."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from previous test"
    tenant_id = pytest.tenant_id

    response = await authenticated_async_client.get(f"/api/v1/tenants/{tenant_id}")
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == tenant_id
    assert data["name"] == TEST_TENANT_NAME


async def test_update_tenant(authenticated_async_client: AsyncClient):
    """Test updating a tenant."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from previous test"
    tenant_id = pytest.tenant_id
    update_data = {"description": "Updated via pytest"}

    response = await authenticated_async_client.put(
        f"/api/v1/tenants/{tenant_id}", json=update_data
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == tenant_id
    assert data["description"] == update_data["description"]


async def test_delete_tenant(authenticated_async_client: AsyncClient):
    """Test deleting a tenant."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from previous test"
    tenant_id = pytest.tenant_id

    response = await authenticated_async_client.delete(f"/api/v1/tenants/{tenant_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text

    # Verify it's gone
    response_get = await authenticated_async_client.get(f"/api/v1/tenants/{tenant_id}")
    assert response_get.status_code == status.HTTP_404_NOT_FOUND
