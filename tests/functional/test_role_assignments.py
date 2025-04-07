import uuid
import pytest
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Removed direct import of TestingSessionLocal
# from virtualstack.db.session import TestingSessionLocal
from virtualstack.models.iam.user_tenant_role import user_tenant_roles_table
from virtualstack.core.permissions import Permission

# TODO: Need a fixture or reliable way to get a role ID if tests run independently
# For now, assume test_roles.py::test_create_role ran and set pytest.role_id

@pytest.mark.asyncio
async def test_assign_role_to_user(
    authenticated_async_client: AsyncClient, # Use superuser client
    db_session: AsyncSession,
):
    """Test assigning a role to a user within a tenant using superuser."""
    # Get IDs from pytest object set by setup_database fixture
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from setup_database"
    tenant_id = pytest.tenant_id
    assert hasattr(pytest, "user2_id"), "User2 ID not set from setup_database" # Use user2
    user_to_assign_id = pytest.user2_id

    # Use the role created during setup instead of a hardcoded UUID
    assert hasattr(pytest, "tenant_admin_role_id"), "Tenant Admin Role ID not set from setup_database"
    role_to_assign_id = pytest.tenant_admin_role_id

    assign_endpoint = f"/api/v1/tenants/{tenant_id}/users/{user_to_assign_id}/roles"

    # --- Action: Attempt to assign the role --- 
    # The endpoint expects the role_id in the body
    response = await authenticated_async_client.post(
        assign_endpoint,
        json={"role_id": str(role_to_assign_id)}
    )

    # --- Assertions --- 
    # Expect success (204 No Content)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # --- Verification Step --- 
    # Check the database directly to confirm the association was created
    stmt = select(user_tenant_roles_table).where(
        and_(
            user_tenant_roles_table.c.user_id == user_to_assign_id,
            user_tenant_roles_table.c.role_id == role_to_assign_id,
            user_tenant_roles_table.c.tenant_id == tenant_id
        )
    )
    result = await db_session.execute(stmt)
    assignment_record = result.fetchone()

    assert assignment_record is not None
    assert assignment_record.user_id == user_to_assign_id
    assert assignment_record.role_id == role_to_assign_id
    assert assignment_record.tenant_id == tenant_id

@pytest.mark.asyncio
async def test_assign_role_to_user_permission_denied(
    authenticated_async_client_user2: AsyncClient, # Use client for user without permission
):
    """Test assigning a role fails when user lacks permission."""
    # Get IDs from pytest object set by setup_database fixture
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from setup_database"
    tenant_id = pytest.tenant_id
    # Attempt to assign role to self (user2) - target user doesn't matter much for perm check
    assert hasattr(pytest, "user2_id"), "User2 ID not set from setup_database"
    user_to_assign_id = pytest.user2_id

    # Use a known role ID (e.g., the tenant admin role created in setup)
    # The specific role doesn't matter for a permission denied test, just needs to exist.
    assert hasattr(pytest, "tenant_admin_role_id"), "Tenant Admin Role ID not set from setup_database"
    role_to_assign_id = pytest.tenant_admin_role_id

    assign_endpoint = f"/api/v1/tenants/{tenant_id}/users/{user_to_assign_id}/roles"

    # --- Action: Attempt to assign the role --- 
    response = await authenticated_async_client_user2.post(
        assign_endpoint,
        json={"role_id": str(role_to_assign_id)}
    )

    # --- Assertions --- 
    # Expect 403 Forbidden
    assert response.status_code == status.HTTP_403_FORBIDDEN

# TODO: Add test for assigning a role the user already has (should still return 204 due to ON CONFLICT)
# TODO: Add test for assigning role to user in different tenant (should fail)
# TODO: Add test for assigning non-existent role (should fail)
# TODO: Add test for assigning role to non-existent user (should fail)
# TODO: Add test for assigning role without correct permissions (should fail)
# TODO: Add test_remove_role_from_user 

@pytest.mark.asyncio
async def test_assign_role_to_user_success(
    authenticated_async_client_tenant_admin: AsyncClient, # Use tenant admin client
    db_session: AsyncSession # Inject db session for verification
) -> None:
    """
    Test successfully assigning a role (Tenant Admin role) to a user (user2)
    by a user with the required permissions (tenant_admin).
    Verified via 204 status and direct DB check.
    """
    # Get IDs from pytest attributes set by setup_database
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set from setup_database"
    tenant_id = pytest.tenant_id
    assert hasattr(pytest, "user2_id"), "User2 ID not set from setup_database"
    user_to_assign_id = pytest.user2_id
    assert hasattr(pytest, "tenant_admin_role_id"), "Tenant Admin Role ID not set from setup_database"
    role_to_assign_id = pytest.tenant_admin_role_id

    assign_endpoint = f"/api/v1/tenants/{tenant_id}/users/{user_to_assign_id}/roles"

    # Use tenant_admin client to assign the tenant admin role to user2
    response = await authenticated_async_client_tenant_admin.post(
        assign_endpoint,
        json={"role_id": str(role_to_assign_id)} # Send role_id in body
    )

    print(f"Assign Role Success - Response status: {response.status_code}")

    # Assert correct status code (204 No Content)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # --- Verification Step --- 
    # Check the database directly to confirm the association was created
    stmt = select(user_tenant_roles_table).where(
        and_(
            user_tenant_roles_table.c.user_id == user_to_assign_id,
            user_tenant_roles_table.c.role_id == role_to_assign_id,
            user_tenant_roles_table.c.tenant_id == tenant_id
        )
    )
    result = await db_session.execute(stmt)
    assignment_record = result.fetchone()

    assert assignment_record is not None, "Role assignment record not found in database"
    assert assignment_record.user_id == user_to_assign_id
    assert assignment_record.role_id == role_to_assign_id
    assert assignment_record.tenant_id == tenant_id
    print(f"DB Verification OK: Role {role_to_assign_id} assigned to user {user_to_assign_id} in tenant {tenant_id}")

# --- Validation Failure Tests --- 

@pytest.mark.asyncio
async def test_assign_role_non_existent_user(
    authenticated_async_client_tenant_admin: AsyncClient,
) -> None:
    """Test assigning role fails when the target user does not exist."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set"
    tenant_id = pytest.tenant_id
    assert hasattr(pytest, "tenant_admin_role_id"), "Role ID not set"
    role_id = pytest.tenant_admin_role_id
    non_existent_user_id = uuid.uuid4() # Generate random UUID

    assign_endpoint = f"/api/v1/tenants/{tenant_id}/users/{non_existent_user_id}/roles"
    response = await authenticated_async_client_tenant_admin.post(
        assign_endpoint,
        json={"role_id": str(role_id)}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "User not found"}

@pytest.mark.asyncio
async def test_assign_role_non_existent_role(
    authenticated_async_client_tenant_admin: AsyncClient,
) -> None:
    """Test assigning role fails when the target role does not exist."""
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set"
    tenant_id = pytest.tenant_id
    assert hasattr(pytest, "user2_id"), "User2 ID not set"
    user_id = pytest.user2_id
    non_existent_role_id = uuid.uuid4() # Generate random UUID

    assign_endpoint = f"/api/v1/tenants/{tenant_id}/users/{user_id}/roles"
    response = await authenticated_async_client_tenant_admin.post(
        assign_endpoint,
        json={"role_id": str(non_existent_role_id)}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Role not found"}

@pytest.mark.asyncio
async def test_assign_role_non_existent_tenant(
    authenticated_async_client_tenant_admin: AsyncClient,
) -> None:
    """Test assigning role fails when the target tenant does not exist."""
    non_existent_tenant_id = uuid.uuid4()
    assert hasattr(pytest, "user2_id"), "User2 ID not set"
    user_id = pytest.user2_id
    assert hasattr(pytest, "tenant_admin_role_id"), "Role ID not set"
    role_id = pytest.tenant_admin_role_id

    assign_endpoint = f"/api/v1/tenants/{non_existent_tenant_id}/users/{user_id}/roles"
    response = await authenticated_async_client_tenant_admin.post(
        assign_endpoint,
        json={"role_id": str(role_id)}
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    # Check that the detail message includes the non-existent tenant ID
    assert f"Tenant {non_existent_tenant_id} not found" in response.json()["detail"]

# TODO: Add test case for assigning a role to a user in a different tenant (400/403/404?)
# Requires clarification on user-tenant relationship validation

@pytest.mark.skip(reason="Needs test redesign with a second tenant fixture to properly test logic.")
@pytest.mark.asyncio
async def test_assign_role_to_user_not_in_tenant(
    authenticated_async_client_tenant_admin: AsyncClient,
    # Need a user who exists but isn't in the default tenant
    # Create a new user and tenant for this test?
    # For now, assume user2 is only in the default tenant and try assigning in a new dummy tenant
) -> None:
    """Test assigning role fails if user doesn't belong to the tenant (has no existing roles)."""
    # Use user2 ID and the tenant admin role ID from setup
    assert hasattr(pytest, "user2_id"), "User2 ID not set"
    user_id = pytest.user2_id
    assert hasattr(pytest, "tenant_admin_role_id"), "Role ID not set"
    role_id = pytest.tenant_admin_role_id
    # Create a new dummy tenant ID for this test
    # In a real scenario, we might need a fixture to create a secondary tenant
    separate_tenant_id = uuid.uuid4()
    
    # We need to simulate the tenant existing, otherwise we get 404 tenant not found
    # This highlights a limitation of the current test setup - ideally, create a real second tenant.
    # For now, this test assumes the tenant *does* exist, but the user has no roles in it.
    # The check user_service.is_user_in_tenant should return False.

    assign_endpoint = f"/api/v1/tenants/{separate_tenant_id}/users/{user_id}/roles"
    response = await authenticated_async_client_tenant_admin.post(
        assign_endpoint,
        json={"role_id": str(role_id)}
    )

    # Expecting 400 Bad Request based on the implemented check
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert f"User {user_id} does not belong to tenant {separate_tenant_id}" in response.text

# TODO: Add test_remove_role_from_user_permission_denied

@pytest.mark.asyncio
async def test_remove_role_from_user_success(
    authenticated_async_client_tenant_admin: AsyncClient,
    db_session: AsyncSession
) -> None:
    """Test successfully removing a role assignment from a user."""
    # --- Setup: Ensure the role assignment exists --- 
    # We'll assign the Tenant Admin role to user2 first
    assert hasattr(pytest, "tenant_id"), "Tenant ID not set"
    tenant_id = pytest.tenant_id
    assert hasattr(pytest, "user2_id"), "User2 ID not set"
    user_id = pytest.user2_id
    assert hasattr(pytest, "tenant_admin_role_id"), "Role ID not set"
    role_id = pytest.tenant_admin_role_id

    assign_endpoint = f"/api/v1/tenants/{tenant_id}/users/{user_id}/roles"
    assign_response = await authenticated_async_client_tenant_admin.post(
        assign_endpoint,
        json={"role_id": str(role_id)}
    )
    assert assign_response.status_code == status.HTTP_204_NO_CONTENT, "Setup failed: Could not assign role first"

    # Verify assignment exists before delete
    stmt_check = select(user_tenant_roles_table).where(
        and_(
            user_tenant_roles_table.c.user_id == user_id,
            user_tenant_roles_table.c.role_id == role_id,
            user_tenant_roles_table.c.tenant_id == tenant_id
        )
    )
    result_check = await db_session.execute(stmt_check)
    assert result_check.fetchone() is not None, "Setup failed: Role assignment not found in DB before delete"

    # --- Action: Call DELETE endpoint --- 
    remove_endpoint = f"/api/v1/tenants/{tenant_id}/users/{user_id}/roles/{role_id}"
    remove_response = await authenticated_async_client_tenant_admin.delete(remove_endpoint)

    # --- Assertions --- 
    assert remove_response.status_code == status.HTTP_204_NO_CONTENT

    # --- Verification: Check DB --- 
    result_check_after = await db_session.execute(stmt_check)
    assert result_check_after.fetchone() is None, "Role assignment still found in DB after delete"
    print(f"DB Verification OK: Role {role_id} successfully removed from user {user_id} in tenant {tenant_id}")

    # --- Idempotency Check (Optional but good) --- 
    # Call DELETE again and expect 404
    remove_response_again = await authenticated_async_client_tenant_admin.delete(remove_endpoint)
    assert remove_response_again.status_code == status.HTTP_404_NOT_FOUND, "DELETE was not idempotent (expected 404 on second call)"

# TODO: Add test_list_user_roles_in_tenant
# TODO: Add test_list_tenant_users_with_roles

# TODO: Add test case for assigning a role that does not exist (404)
# TODO: Add test case for assigning a role to a user that does not exist (404)
# TODO: Add test case for assigning a role to a user in a different tenant (403/404 depending on visibility) 