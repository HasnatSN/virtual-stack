from uuid import uuid4

from fastapi import status
from httpx import AsyncClient
import pytest
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import pytest_asyncio


# Test data
# TEST_ROLE = {"name": f"pytest-role-{uuid4()}", "description": "Role created via pytest"} # Old test data

# Use a UUID for the tenant_id placeholder (though roles are global now)
# TEST_TENANT_ID = uuid4()

# Store a known permission ID from the seeded data (found via code inspection)
# TODO: Ideally, create a fixture or helper to fetch a specific seeded permission ID
# Using vm:read for now
# seeded_permission_id_vm_read = "f420e148-166e-4601-8a3f-e9f1b9479d31" # REMOVED HARDCODED ID

@pytest_asyncio.fixture(scope="function")
async def test_role(authenticated_async_client: AsyncClient) -> dict:
    """Fixture to create a role via API and clean it up afterwards."""
    role_data = {
        "name": f"Fixture Role {uuid4()}",
        "description": "A role created by the test_role fixture",
        "permissions": [],
    }
    created_role = None
    try:
        response = await authenticated_async_client.post("/api/v1/roles/", json=role_data)
        response.raise_for_status()  # Raise exception for bad status codes
        created_role = response.json()
        assert "id" in created_role
        yield created_role
    finally:
        if created_role and "id" in created_role:
            role_id = created_role["id"]
            print(f"\nCleaning up role ID: {role_id}")
            delete_response = await authenticated_async_client.delete(f"/api/v1/roles/{role_id}")
            if delete_response.status_code not in [status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND]:
                print(f"WARNING: Failed to cleanup role {role_id}. Status: {delete_response.status_code}, Text: {delete_response.text}")


@pytest.mark.asyncio
async def test_create_role(authenticated_async_client: AsyncClient):
    """Test creating a new role."""
    role_data = {
        "name": f"Test Global Role {uuid4()}", # Renamed for clarity
        "description": "A global role created for testing",
        "permissions": [], # Assuming permissions are handled separately or start empty
    }
    response = await authenticated_async_client.post("/api/v1/roles/", json=role_data)
    assert response.status_code == status.HTTP_201_CREATED, f"Failed: {response.text}"
    data = response.json()
    assert data["name"] == role_data["name"]
    assert "id" in data
    # pytest.role_id = data["id"] # --- REMOVED --- Store for subsequent tests
    # Cleanup is handled by deleting the role if created by fixture, or manually if needed.
    # For this specific test, we might want to delete the role it created.
    role_id_to_delete = data["id"]
    await authenticated_async_client.delete(f"/api/v1/roles/{role_id_to_delete}")


@pytest.mark.asyncio
async def test_get_role_by_id(authenticated_async_client: AsyncClient, test_role: dict):
    """Test getting a role by ID using the test_role fixture."""
    # assert hasattr(pytest, "role_id"), "Role ID not set from previous test" # REMOVED
    role_id = test_role["id"]
    response = await authenticated_async_client.get(f"/api/v1/roles/{role_id}")
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert data["id"] == role_id
    assert data["name"] == test_role["name"]


@pytest.mark.asyncio
async def test_list_roles_for_tenant(authenticated_async_client: AsyncClient, test_role: dict):
    """Test listing global roles, ensuring the fixture role is present."""
    # Role ID must exist from the fixture
    role_id = test_role["id"]

    response = await authenticated_async_client.get("/api/v1/roles/")
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    # Check if the created role is in the list
    found = any(item["id"] == role_id for item in data)
    assert found, f"Fixture role {role_id} not found in global list"


@pytest.mark.asyncio
async def test_update_role(authenticated_async_client: AsyncClient, test_role: dict):
    """Test updating a role using the test_role fixture."""
    role_id = test_role["id"]
    update_data = {"description": "Updated fixture role description"}
    response = await authenticated_async_client.put(f"/api/v1/roles/{role_id}", json=update_data)
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert data["id"] == role_id
    assert data["description"] == update_data["description"]
    assert data["name"] == test_role["name"] # Name should not change

# --- SKIPPED TESTS REMAIN --- 
@pytest.mark.skip(reason="Permission assignment service logic is currently disabled")
def test_add_permission_to_role():
    """Test adding a permission to a role (currently skipped)."""


@pytest.mark.skip(reason="Permission assignment service logic is currently disabled")
def test_remove_permission_from_role():
    """Test removing a permission from a role (currently skipped)."""


@pytest.mark.asyncio
async def test_delete_role(authenticated_async_client: AsyncClient):
    """Test deleting a role (creates its own role for deletion)."""
    # Create a role specifically for this test to delete
    role_data = {
        "name": f"Delete Me Role {uuid4()}",
        "description": "Role to be deleted",
        "permissions": [],
    }
    create_response = await authenticated_async_client.post("/api/v1/roles/", json=role_data)
    assert create_response.status_code == status.HTTP_201_CREATED
    role_to_delete = create_response.json()
    role_id = role_to_delete["id"]

    # Now delete it
    response = await authenticated_async_client.delete(f"/api/v1/roles/{role_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT, f"Failed: {response.text}"

    # Verify the role is actually deleted
    response_get = await authenticated_async_client.get(f"/api/v1/roles/{role_id}")
    assert response_get.status_code == status.HTTP_404_NOT_FOUND

# --- Role Permission Tests (using fixture) --- 

@pytest.mark.asyncio
async def test_add_permission_to_role_success(
    authenticated_async_client: AsyncClient,
    db_session: AsyncSession, # Inject db for verification
    test_role: dict # Use the fixture role
) -> None:
    """Test successfully adding a permission to the fixture role."""
    role_id = test_role["id"]
    # Use the seeded permission ID from pytest attribute
    assert hasattr(pytest, "seeded_permission_id_vm_read"), "Seeded permission ID not set in conftest"
    permission_id_to_add = pytest.seeded_permission_id_vm_read
    assert permission_id_to_add is not None, "VM_READ permission was not seeded correctly."

    endpoint = f"/api/v1/roles/{role_id}/permissions"
    response = await authenticated_async_client.post(
        endpoint,
        json={"permission_id": str(permission_id_to_add)}
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT, f"Failed: {response.text}"

    # Verify in DB
    from virtualstack.models.iam.role_permissions import role_permissions_table
    stmt = select(role_permissions_table).where(
        and_(
            role_permissions_table.c.role_id == uuid.UUID(role_id),
            # Use cast to ensure comparison with UUID type works reliably
            role_permissions_table.c.permission_id == permission_id_to_add
        )
    )
    result = await db_session.execute(stmt)
    association = result.first()
    assert association is not None
    # Compare string representations for UUIDs from different sources
    assert str(association.permission_id) == str(permission_id_to_add)

@pytest.mark.asyncio
async def test_list_role_permissions_success(
    authenticated_async_client: AsyncClient,
    test_role: dict # Use the fixture role
) -> None:
    """Test listing permissions for the fixture role after adding one."""
    role_id = test_role["id"]
    # Use the seeded permission ID from pytest attribute
    assert hasattr(pytest, "seeded_permission_id_vm_read"), "Seeded permission ID not set in conftest"
    permission_id_added = pytest.seeded_permission_id_vm_read
    assert permission_id_added is not None, "VM_READ permission was not seeded correctly."

    # Add the permission first for this isolated test
    add_endpoint = f"/api/v1/roles/{role_id}/permissions"
    add_response = await authenticated_async_client.post(
        add_endpoint,
        json={"permission_id": str(permission_id_added)}
    )
    assert add_response.status_code == status.HTTP_204_NO_CONTENT, "Setup failed: Could not add permission"

    # Now list
    list_endpoint = f"/api/v1/roles/{role_id}/permissions"
    response = await authenticated_async_client.get(list_endpoint)

    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    permissions_list = response.json()
    assert isinstance(permissions_list, list)
    # Check if the added permission is in the list (comparing string representations)
    found = any(str(item.get("id")) == str(permission_id_added) for item in permissions_list)
    assert found, f"Permission {permission_id_added} not found in list for role {role_id}: {permissions_list}"

@pytest.mark.asyncio
async def test_remove_permission_from_role_success(
    authenticated_async_client: AsyncClient,
    db_session: AsyncSession, # Inject db for verification
    test_role: dict # Use the fixture role
) -> None:
    """Test successfully removing a permission from the fixture role."""
    role_id = test_role["id"]
    # Use the seeded permission ID from pytest attribute
    assert hasattr(pytest, "seeded_permission_id_vm_read"), "Seeded permission ID not set in conftest"
    permission_id_to_remove = pytest.seeded_permission_id_vm_read
    assert permission_id_to_remove is not None, "VM_READ permission was not seeded correctly."

    # Add the permission first to ensure it exists
    add_endpoint = f"/api/v1/roles/{role_id}/permissions"
    add_response = await authenticated_async_client.post(
        add_endpoint,
        json={"permission_id": str(permission_id_to_remove)}
    )
    assert add_response.status_code == status.HTTP_204_NO_CONTENT, "Setup failed: Could not add permission"

    # Verify it exists before delete (belt and suspenders)
    from virtualstack.models.iam.role_permissions import role_permissions_table
    stmt_check = select(role_permissions_table).where(
        and_(
            role_permissions_table.c.role_id == uuid.UUID(role_id),
            role_permissions_table.c.permission_id == permission_id_to_remove # Compare UUID directly
        )
    )
    check_result = await db_session.execute(stmt_check)
    assert check_result.fetchone() is not None, "Role-permission link not found in DB before delete"

    # Action: Remove permission
    remove_endpoint = f"/api/v1/roles/{role_id}/permissions/{permission_id_to_remove}"
    response = await authenticated_async_client.delete(remove_endpoint)

    assert response.status_code == status.HTTP_204_NO_CONTENT, f"Failed: {response.text}"

    # Verify in DB that it's gone
    stmt_verify = select(func.count(role_permissions_table.c.role_id)).select_from(role_permissions_table).where(
        and_(
            role_permissions_table.c.role_id == uuid.UUID(role_id),
            role_permissions_table.c.permission_id == permission_id_to_remove # Compare UUID directly
        )
    )
    verify_result = await db_session.execute(stmt_verify)
    assert verify_result.fetchone()[0] == 0, "Role-permission link still found in DB after delete"

    # Idempotency check: remove again, expect 404
    response_again = await authenticated_async_client.delete(remove_endpoint)
    assert response_again.status_code == status.HTTP_404_NOT_FOUND, "Expected 404 on second delete call"

# TODO: Add failure tests for role permission management (e.g., add non-existent permission, remove non-assigned permission)
