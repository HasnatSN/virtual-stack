from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
import pytest


# Test data
TEST_INVITATION_EMAIL = f"pytest-invite-{uuid4()}@virtualstack.example"
TEST_INVITATION = {
    "email": TEST_INVITATION_EMAIL
    # role_id will be added later if needed for creation test
}

# We need authenticated client and tenant_id/role_id for these tests
# TODO: Create fixtures for authenticated client, tenant, role
pytestmark = pytest.mark.skip(reason="Requires authenticated client, tenant, and role fixtures")


@pytest.fixture(scope="module", autouse=True)
def _setup_invitation_dependencies(authenticated_async_client: TestClient):
    """Creates necessary Tenant and potentially Role for invitation tests."""
    # Create a tenant first
    tenant_data = {"name": f"Test Tenant Invitations {uuid4()}"}
    response = authenticated_async_client.post("/api/v1/tenants/", json=tenant_data)
    assert response.status_code == status.HTTP_201_CREATED, f"Failed to create tenant: {response.text}"
    pytest.tenant_id = response.json()["id"]
    # TODO: Create a role when roles are testable, store its ID in pytest.role_id
    # For now, we'll proceed without a real role ID
    print(f"Tenant for invitation tests created: {pytest.tenant_id}")


def test_create_invitation(client: TestClient):
    """Test creating a new invitation."""
    headers = {"Authorization": "Bearer MOCK_TOKEN"} # TODO: Replace with real token via fixture
    tenant_id = getattr(pytest, 'tenant_id', None)
    # role_id = getattr(pytest, 'role_id', None) # Role dependency disabled
    assert tenant_id is not None, "Tenant ID fixture needed"
    # assert role_id is not None, "Role ID fixture needed" # Role dependency disabled

    invitation_data = {
        "email": "invited.user@example.com",
        "tenant_id": tenant_id,
        # "role_id": role_id, # Role dependency disabled
        "expires_in_days": 1, # Short expiry for testing
    }
    response = client.post("/api/v1/invitations/", headers=headers, json=invitation_data)
    assert response.status_code == status.HTTP_201_CREATED, f"Failed: {response.text}"
    data = response.json()
    assert data["email"] == "invited.user@example.com"
    assert data["tenant_id"] == tenant_id
    # assert data["role_id"] == role_id # Role dependency disabled
    assert data["status"] == "pending"
    assert "token" in data # Check if the token is included in creation response

    pytest.invitation_id = data["id"]
    pytest.invitation_token = data["token"]


def test_extract_token_from_link():
    """Test extracting token from the verification link."""
    link = f"http://frontend.example.com/verify-invitation?token={pytest.invitation_token}"
    # Simulate frontend or user extracting the token
    token = link.split("token=")[-1]
    assert token == pytest.invitation_token


def test_verify_invitation_token(client: TestClient):
    """Test verifying an invitation token."""
    assert hasattr(pytest, "invitation_token"), "Invitation token not set"
    token = pytest.invitation_token
    response = client.post("/api/v1/invitations/verify", json={"token": token})
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert data["valid"] is True
    assert data["email"] == "invited.user@example.com"
    assert data["tenant_id"] == pytest.tenant_id
    assert data["token"] == token


def test_verify_invalid_token(client: TestClient):
    """Test verifying an invalid invitation token."""
    response = client.post("/api/v1/invitations/verify", json={"token": "invalid-token"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert data["detail"] == "Invalid or expired invitation token"
    # assert data["valid"] is False # Optional check depending on desired response structure


def test_get_invitation_by_id(client: TestClient):
    """Test getting invitation details by ID."""
    assert hasattr(pytest, "invitation_id"), "Invitation ID not set"
    invitation_id = pytest.invitation_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    response = client.get(f"/api/v1/invitations/{invitation_id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert data["id"] == invitation_id
    assert data["email"] == "invited.user@example.com"
    assert data["tenant_id"] == pytest.tenant_id
    assert data["status"] == "pending" # Assuming it hasn't expired/been revoked yet


def test_list_pending_invitations(client: TestClient):
    """Test listing pending invitations for the tenant."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set"
    tenant_id = pytest.tenant_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    response = client.get(f"/api/v1/invitations/?tenant_id={tenant_id}&status=pending", headers=headers)
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    found = any(inv["id"] == pytest.invitation_id for inv in data)
    assert found, "Created invitation not found in tenant list"


def test_revoke_invitation(client: TestClient):
    """Test revoking an invitation."""
    assert hasattr(pytest, "invitation_id"), "Invitation ID not set"
    invitation_id = pytest.invitation_id
    headers = {"Authorization": "Bearer MOCK_TOKEN"}
    response = client.post(f"/api/v1/invitations/{invitation_id}/revoke", headers=headers)
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert data["id"] == invitation_id
    assert data["status"] == "revoked"

    # Verify token is now invalid
    token = pytest.invitation_token
    response_verify = client.post("/api/v1/invitations/verify", json={"token": token})
    assert response_verify.status_code == status.HTTP_400_BAD_REQUEST
    assert response_verify.json()["detail"] == "Invalid or expired invitation token"

    # Verify list doesn't show it as pending
    response_list = client.get(f"/api/v1/invitations/?tenant_id={pytest.tenant_id}&status=pending", headers=headers)
    assert response_list.status_code == status.HTTP_200_OK
    found_pending = any(inv["id"] == invitation_id for inv in response_list.json())
    assert not found_pending, "Revoked invitation still found in pending list"

    # Removed commented-out code for checking revoked status via GET /id

    # Verify it cannot be verified anymore
    assert hasattr(pytest, "invitation_token"), "Invitation token not set"
    token = pytest.invitation_token
    response_verify = client.post("/api/v1/invitations/verify", json={"token": token})
    assert response_verify.status_code == status.HTTP_200_OK
    assert response_verify.json()["valid"] is False

    # Verify get by ID shows revoked status (requires service/model update)
    # response_get = client.get(f"/api/v1/invitations/{invitation_id}", headers=headers)
    # assert response_get.status_code == status.HTTP_200_OK
    # assert response_get.json()["status"] == "revoked"
