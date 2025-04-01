from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
import pytest


# Test data
TEST_ROLE = {"name": f"pytest-role-{uuid4()}", "description": "Role created via pytest"}

# Use a UUID for the tenant_id placeholder
TEST_TENANT_ID = uuid4()

# Mark all tests in this module to be skipped for now
pytestmark = pytest.mark.skip(reason="Role tests depend on Tenant features and may need fixture updates")


def test_create_role(client: TestClient):
    """Test creating a new role."""
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    tenant_id = getattr(pytest, 'tenant_id', TEST_TENANT_ID)
    role_data = {
        "name": f"Test Role {uuid4()}",
        "description": "A role created for testing",
        "tenant_id": str(tenant_id),
        "permissions": [],
    }
    response = client.post("/api/v1/roles/", headers=headers, json=role_data)
    assert response.status_code == status.HTTP_201_CREATED, f"Failed: {response.text}"
    data = response.json()
    assert data["name"] == role_data["name"]
    assert data["tenant_id"] == str(tenant_id)
    assert "id" in data
    pytest.role_id = data["id"]


def test_get_role_by_id(client: TestClient):
    """Test getting a role by ID."""
    assert hasattr(pytest, "role_id"), "Role ID not set from previous test"
    role_id = pytest.role_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    response = client.get(f"/api/v1/roles/{role_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert data["id"] == role_id
    # Add more assertions based on expected role details


def test_list_roles_for_tenant(client: TestClient):
    """Test listing roles for the test tenant."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from previous test"
    tenant_id = getattr(pytest, 'tenant_id', TEST_TENANT_ID)
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    response = client.get(f"/api/v1/roles/?tenant_id={tenant_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    # Check if the created role is in the list
    found = any(item["id"] == pytest.role_id for item in data if hasattr(pytest, "role_id"))
    assert found, "Created role not found in tenant list"


def test_update_role(client: TestClient):
    """Test updating a role."""
    assert hasattr(pytest, "role_id"), "Role ID not set from previous test"
    role_id = pytest.role_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    update_data = {"description": "Updated role description"}
    response = client.put(f"/api/v1/roles/{role_id}", headers=headers, json=update_data)
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert data["id"] == role_id
    assert data["description"] == update_data["description"]


@pytest.mark.skip(reason="Permission assignment service logic is currently disabled")
def test_add_permission_to_role():
    """Test adding a permission to a role (currently skipped)."""


@pytest.mark.skip(reason="Permission assignment service logic is currently disabled")
def test_remove_permission_from_role():
    """Test removing a permission from a role (currently skipped)."""


def test_delete_role(client: TestClient):
    """Test deleting a role."""
    assert hasattr(pytest, "role_id"), "Role ID not set from previous test"
    role_id = pytest.role_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    response = client.delete(f"/api/v1/roles/{role_id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT, f"Failed: {response.text}"

    # Verify the role is actually deleted
    response_get = client.get(f"/api/v1/roles/{role_id}", headers=headers)
    assert response_get.status_code == status.HTTP_404_NOT_FOUND
