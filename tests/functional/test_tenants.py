import pytest
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

# Test data
TEST_TENANT = {
    "name": "Pytest Tenant",
    "slug": f"pytest-tenant-{uuid4()}", # Ensure unique slug
    "description": "Tenant created via pytest"
}

# We need authenticated client for these tests
# TODO: Create a fixture for authenticated client later
pytestmark = pytest.mark.skip(reason="Requires authenticated client fixture")

def test_create_tenant(client: TestClient, db_session: AsyncSession):
    """Test creating a new tenant."""
    # Need auth token first - skip for now
    headers = {"Authorization": "Bearer MOCK_TOKEN"} 
    
    response = client.post(
        "/api/v1/tenants/", 
        json=TEST_TENANT,
        headers=headers 
    )
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["name"] == TEST_TENANT["name"]
    assert data["slug"] == TEST_TENANT["slug"]
    assert "id" in data
    
    # Store ID for next test
    pytest.tenant_id = data["id"]


def test_get_tenant_by_id(client: TestClient, db_session: AsyncSession):
    """Test getting a tenant by ID."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from previous test"
    tenant_id = pytest.tenant_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}

    response = client.get(f"/api/v1/tenants/{tenant_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == tenant_id
    assert data["name"] == TEST_TENANT["name"]


def test_get_tenant_by_slug(client: TestClient, db_session: AsyncSession):
    """Test getting a tenant by slug."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from previous test"
    slug = TEST_TENANT["slug"]
    headers = {"Authorization": "Bearer MOCK_TOKEN"}

    response = client.get(f"/api/v1/tenants/slug/{slug}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["slug"] == slug
    assert data["name"] == TEST_TENANT["name"]


def test_update_tenant(client: TestClient, db_session: AsyncSession):
    """Test updating a tenant."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from previous test"
    tenant_id = pytest.tenant_id
    update_data = {"description": "Updated via pytest"}
    headers = {"Authorization": "Bearer MOCK_TOKEN"}

    response = client.put(
        f"/api/v1/tenants/{tenant_id}", 
        json=update_data,
        headers=headers
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == tenant_id
    assert data["description"] == update_data["description"]


def test_delete_tenant(client: TestClient, db_session: AsyncSession):
    """Test deleting a tenant."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from previous test"
    tenant_id = pytest.tenant_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}

    response = client.delete(f"/api/v1/tenants/{tenant_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, response.text # Delete returns the object

    # Verify it's gone
    response_get = client.get(f"/api/v1/tenants/{tenant_id}", headers=headers)
    assert response_get.status_code == status.HTTP_404_NOT_FOUND 