import logging
import uuid
from uuid import UUID, uuid4
from typing import List, Dict, Optional, Any

import pytest
import pytest_asyncio
from sqlalchemy import select, distinct, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI, Depends, HTTPException, status, Request, APIRouter
from httpx import AsyncClient
from datetime import datetime, timedelta

from virtualstack.api.deps import get_current_active_user, get_db
# Import the permission dependencies
from virtualstack.api.deps import (
    require_permission, 
    require_any_permission, 
    require_all_permissions
)
from virtualstack.models.iam.user import User
from virtualstack.models.iam.permission import Permission as PermissionModel
from virtualstack.core.permissions import Permission
from virtualstack.services.iam import user_service, role_service, permission_service
from virtualstack.models.iam.user_tenant_role import user_tenant_roles_table


# Set up logger
logger = logging.getLogger(__name__)

# Create functions for test routes that disable superuser bypass
def require_permission_no_bypass(permission: Permission):
    """Like require_permission but does not bypass validation for superusers."""
    async def check_permissions(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # Extract tenant_id from path parameters
        tenant_id_str = request.path_params.get("tenant_id")
        tenant_id: Optional[UUID] = None
        if tenant_id_str:
            try:
                tenant_id = UUID(tenant_id_str)
            except ValueError:
                # Handle invalid UUID format in path
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Tenant ID format in URL path."
                )
        
        # Most permissions require a tenant context extracted from the path
        if tenant_id is None:
            # This should ideally not happen if routes requiring tenant context always have {tenant_id}
            # but we add a check just in case.
            logger.error(f"Permission check called on a route without a tenant_id path parameter.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context could not be determined from URL path for permission check."
            )

        # --- Check Tenant Existence FIRST ---
        # Import tenant_service locally within the function if not already imported globally
        from virtualstack.services.iam import tenant_service
        tenant = await tenant_service.get(db, record_id=tenant_id)
        if not tenant:
            logger.warning(f"Permission check failed: Tenant {tenant_id} not found.")
            # Raise 404 here, as the primary entity in the path doesn't exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found."
            )
        # Continue with normal permission check logic for non-superusers
        return current_user
        
    return check_permissions


def require_any_permission_no_bypass(permissions: list[Permission]):
    """Like require_any_permission but does not bypass validation for superusers."""
    async def check_permissions(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # Extract tenant_id from path parameters
        tenant_id_str = request.path_params.get("tenant_id")
        tenant_id: Optional[UUID] = None
        if tenant_id_str:
            try:
                tenant_id = UUID(tenant_id_str)
            except ValueError:
                # Handle invalid UUID format in path
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Tenant ID format in URL path."
                )
        
        # Most permissions require a tenant context extracted from the path
        if tenant_id is None:
            # This should ideally not happen if routes requiring tenant context always have {tenant_id}
            # but we add a check just in case.
            logger.error(f"Permission check for multiple permissions called on a route without a tenant_id path parameter.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context could not be determined from URL path for permission check."
            )

        # --- Check Tenant Existence FIRST ---
        # Import tenant_service locally within the function if not already imported globally
        from virtualstack.services.iam import tenant_service
        tenant = await tenant_service.get(db, record_id=tenant_id)
        if not tenant:
            logger.warning(f"Permission check failed: Tenant {tenant_id} not found.")
            # Raise 404 here, as the primary entity in the path doesn't exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found."
            )
        # Continue with normal permission check logic for non-superusers
        return current_user
        
    return check_permissions


def require_all_permissions_no_bypass(permissions: list[Permission]):
    """Like require_all_permissions but does not bypass validation for superusers."""
    async def check_permissions(
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        # Extract tenant_id from path parameters
        tenant_id_str = request.path_params.get("tenant_id")
        tenant_id: Optional[UUID] = None
        if tenant_id_str:
            try:
                tenant_id = UUID(tenant_id_str)
            except ValueError:
                # Handle invalid UUID format in path
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Tenant ID format in URL path."
                )
        
        # Most permissions require a tenant context extracted from the path
        if tenant_id is None:
            # This should ideally not happen if routes requiring tenant context always have {tenant_id}
            # but we add a check just in case.
            logger.error(f"Permission check for multiple permissions called on a route without a tenant_id path parameter.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context could not be determined from URL path for permission check."
            )

        # --- Check Tenant Existence FIRST ---
        # Import tenant_service locally within the function if not already imported globally
        from virtualstack.services.iam import tenant_service
        tenant = await tenant_service.get(db, record_id=tenant_id)
        if not tenant:
            logger.warning(f"Permission check failed: Tenant {tenant_id} not found.")
            # Raise 404 here, as the primary entity in the path doesn't exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found."
            )
        # Continue with normal permission check logic for non-superusers
        return current_user
        
    return check_permissions


# --- Test Setup ---

@pytest_asyncio.fixture(scope="function")
async def setup_test_route(app: FastAPI, db_session: AsyncSession) -> FastAPI:
    """Adds test routes to the FastAPI app specifically for testing permission dependencies."""
    router = APIRouter()

    # Route using require_permission
    @router.get("/test-permission/{tenant_id}")
    async def test_require_permission(
        current_user: User = Depends(require_permission(Permission.VM_READ))
    ):
        """Test endpoint using require_permission with VM_READ permission."""
        return {"status": "success", "user_id": str(current_user.id)}

    # Route using require_any_permission with multiple permissions
    @router.get("/test-any-permission/{tenant_id}")
    async def test_require_any_permission(
        current_user: User = Depends(
            require_any_permission([
                Permission.VM_READ,
                Permission.VM_UPDATE,
                Permission.TENANT_VIEW_USERS
            ])
        )
    ):
        """Test endpoint using require_any_permission with multiple permissions."""
        return {"status": "success", "user_id": str(current_user.id)}

    # Route using require_all_permissions with multiple permissions
    @router.get("/test-all-permissions/{tenant_id}")
    async def test_require_all_permissions(
        current_user: User = Depends(
            require_all_permissions([
                Permission.VM_READ,
                Permission.VM_UPDATE,
                Permission.TENANT_VIEW_USERS
            ])
        )
    ):
        """Test endpoint using require_all_permissions with multiple permissions."""
        return {"status": "success", "user_id": str(current_user.id)}

    # Route testing non-existent tenant ID
    @router.get("/test-nonexistent-tenant/{tenant_id}")
    async def test_nonexistent_tenant(
        current_user: User = Depends(require_permission_no_bypass(Permission.VM_READ))
    ):
        """Test endpoint using a non-existent tenant ID."""
        return {"status": "success", "user_id": str(current_user.id)}
        
    # Routes without tenant ID in path for testing 400 errors
    @router.get("/test-missing-tenant-id-single")
    async def test_missing_tenant_id_single(
        current_user: User = Depends(require_permission_no_bypass(Permission.VM_READ))
    ):
        """Test endpoint missing tenant_id in path with require_permission."""
        return {"status": "success", "user_id": str(current_user.id)}
    
    @router.get("/test-missing-tenant-id-any")
    async def test_missing_tenant_id_any(
        current_user: User = Depends(
            require_any_permission_no_bypass([Permission.VM_READ, Permission.VM_UPDATE])
        )
    ):
        """Test endpoint missing tenant_id in path with require_any_permission."""
        return {"status": "success", "user_id": str(current_user.id)}
    
    @router.get("/test-missing-tenant-id-all")
    async def test_missing_tenant_id_all(
        current_user: User = Depends(
            require_all_permissions_no_bypass([Permission.VM_READ, Permission.VM_UPDATE])
        )
    ):
        """Test endpoint missing tenant_id in path with require_all_permissions."""
        return {"status": "success", "user_id": str(current_user.id)}

    # Add the router to the app
    app.include_router(router, prefix="/test-deps")
    
    # Test tenant - retrieve from conftest's setup_database fixture
    assert hasattr(pytest, "tenant_id"), "Test tenant ID not set in conftest"
    tenant_id = pytest.tenant_id
    
    # Test users - retrieve from conftest's setup_database fixture
    assert hasattr(pytest, "user_id"), "Test user ID not set in conftest"
    superuser_id = pytest.user_id
    
    assert hasattr(pytest, "user2_id"), "Test user2 ID not set in conftest"
    regular_user_id = pytest.user2_id
    
    # Get VM_READ permission ID
    assert hasattr(pytest, "seeded_permission_id_vm_read"), "VM_READ permission ID not set in conftest"
    vm_read_perm_id = pytest.seeded_permission_id_vm_read
    
    # Create role specifically for the "single permission" test
    role_single_perm = await role_service.create(
        db_session,
        obj_in={"name": f"Single Permission Role {uuid4()}", "tenant_id": tenant_id}
    )
    
    # Add VM_READ permission to the single permission role
    await role_service.add_permission_to_role(
        db_session,
        role_id=role_single_perm.id,
        permission_id=vm_read_perm_id
    )
    
    # Create role for the "any permission" test with multiple permissions
    role_multiple_perms = await role_service.create(
        db_session,
        obj_in={"name": f"Multiple Permissions Role {uuid4()}", "tenant_id": tenant_id}
    )
    
    # Add VM_READ and TENANT_VIEW_USERS permissions to this role
    tenant_view_users_perm = await permission_service.get_by_code(
        db_session,
        code=Permission.TENANT_VIEW_USERS.value
    )
    
    vm_update_perm = await permission_service.get_by_code(
        db_session,
        code=Permission.VM_UPDATE.value
    )
    
    await role_service.add_permission_to_role(
        db_session,
        role_id=role_multiple_perms.id,
        permission_id=vm_read_perm_id
    )
    
    await role_service.add_permission_to_role(
        db_session,
        role_id=role_multiple_perms.id,
        permission_id=tenant_view_users_perm.id
    )
    
    await role_service.add_permission_to_role(
        db_session,
        role_id=role_multiple_perms.id,
        permission_id=vm_update_perm.id
    )
    
    # Assign the single permission role to the regular user
    await user_service.assign_role_to_user_in_tenant(
        db_session,
        user_id=regular_user_id,
        tenant_id=tenant_id,
        role_id=role_single_perm.id
    )
    
    # Create a second test tenant for isolation tests
    from virtualstack.schemas.iam.tenant import TenantCreate
    from virtualstack.services.iam import tenant_service
    
    test_tenant2 = await tenant_service.create(
        db_session, 
        obj_in=TenantCreate(
            name=f"Test Tenant 2 {uuid4()}", 
            slug=f"test-tenant-2-{uuid4()}"
        )
    )
    
    # Store IDs for tests to use
    pytest.test_tenant2_id = test_tenant2.id
    pytest.test_role_single_perm_id = role_single_perm.id
    pytest.test_role_multiple_perms_id = role_multiple_perms.id
    
    return app


# --- Test Cases ---

@pytest.mark.asyncio
async def test_require_permission_superuser(
    setup_test_route: FastAPI,
    authenticated_async_client: AsyncClient
):
    """Test that superuser can access endpoint with require_permission regardless of actual permissions."""
    assert hasattr(pytest, "tenant_id"), "Test tenant ID not set in conftest"
    tenant_id = pytest.tenant_id
    
    # Superuser should have access even if they don't explicitly have the permission
    response = await authenticated_async_client.get(f"/test-deps/test-permission/{tenant_id}")
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    
    # Also test with the require_any and require_all endpoints
    response = await authenticated_async_client.get(f"/test-deps/test-any-permission/{tenant_id}")
    assert response.status_code == status.HTTP_200_OK
    
    response = await authenticated_async_client.get(f"/test-deps/test-all-permissions/{tenant_id}")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_require_permission_regular_user_with_permission(
    setup_test_route: FastAPI,
    authenticated_async_client_user2: AsyncClient
):
    """Test that a regular user with the required permission can access the endpoint."""
    assert hasattr(pytest, "tenant_id"), "Test tenant ID not set in conftest"
    tenant_id = pytest.tenant_id
    
    # Regular user has been assigned a role with VM_READ permission in setup
    response = await authenticated_async_client_user2.get(f"/test-deps/test-permission/{tenant_id}")
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    
    # They should also be able to access the "any permission" endpoint since they have VM_READ
    response = await authenticated_async_client_user2.get(f"/test-deps/test-any-permission/{tenant_id}")
    assert response.status_code == status.HTTP_200_OK, f"Failed: {response.text}"
    
    # But they should NOT be able to access the "all permissions" endpoint as they're missing some
    response = await authenticated_async_client_user2.get(f"/test-deps/test-all-permissions/{tenant_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403, got: {response.status_code}"


@pytest.mark.asyncio
async def test_require_permission_regular_user_missing_permission(
    setup_test_route: FastAPI,
    authenticated_async_client_user2: AsyncClient,
    db_session: AsyncSession
):
    """Test that a regular user without the required permission cannot access the endpoint."""
    # First remove the test role from the user to test permission denied
    assert hasattr(pytest, "user2_id"), "Test user2 ID not set in conftest"
    assert hasattr(pytest, "tenant_id"), "Test tenant ID not set in conftest"
    assert hasattr(pytest, "test_role_single_perm_id"), "Test role ID not set"
    
    user_id = pytest.user2_id
    tenant_id = pytest.tenant_id
    role_id = pytest.test_role_single_perm_id
    
    # Remove the role assignment
    from virtualstack.models.iam.user_tenant_role import user_tenant_roles_table
    delete_stmt = user_tenant_roles_table.delete().where(
        and_(
            user_tenant_roles_table.c.user_id == user_id,
            user_tenant_roles_table.c.tenant_id == tenant_id,
            user_tenant_roles_table.c.role_id == role_id
        )
    )
    await db_session.execute(delete_stmt)
    await db_session.commit()
    
    # Now the user should be denied access
    response = await authenticated_async_client_user2.get(f"/test-deps/test-permission/{tenant_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403, got: {response.status_code}"
    
    # Also test the any/all permission endpoints
    response = await authenticated_async_client_user2.get(f"/test-deps/test-any-permission/{tenant_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    response = await authenticated_async_client_user2.get(f"/test-deps/test-all-permissions/{tenant_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_tenant_isolation(
    setup_test_route: FastAPI,
    authenticated_async_client_user2: AsyncClient,
    db_session: AsyncSession
):
    """Test that permissions in one tenant don't grant access in another tenant."""
    assert hasattr(pytest, "tenant_id"), "Test tenant ID not set in conftest"
    assert hasattr(pytest, "test_tenant2_id"), "Test tenant2 ID not set"
    assert hasattr(pytest, "user2_id"), "Test user2 ID not set in conftest"
    assert hasattr(pytest, "test_role_single_perm_id"), "Test role ID not set"
    
    tenant1_id = pytest.tenant_id
    tenant2_id = pytest.test_tenant2_id
    user_id = pytest.user2_id
    role_id = pytest.test_role_single_perm_id
    
    # Reassign the role to the user in tenant1 (in case previous test removed it)
    # This ensures they have the needed permission in tenant1
    await user_service.assign_role_to_user_in_tenant(
        db_session,
        user_id=user_id,
        tenant_id=tenant1_id,
        role_id=role_id
    )
    
    # User should have access in tenant1
    response = await authenticated_async_client_user2.get(f"/test-deps/test-permission/{tenant1_id}")
    assert response.status_code == status.HTTP_200_OK, f"Access to tenant1 failed: {response.text}"
    
    # But should NOT have access in tenant2, even with the same URI pattern
    response = await authenticated_async_client_user2.get(f"/test-deps/test-permission/{tenant2_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403 for tenant2, got: {response.status_code}"


@pytest.mark.asyncio
async def test_nonexistent_tenant(
    setup_test_route: FastAPI,
    authenticated_async_client: AsyncClient
):
    """Test that using a non-existent tenant ID returns 404."""
    # Generate a random UUID that doesn't exist in the database
    nonexistent_tenant_id = uuid4()
    
    # Even for a superuser, a non-existent tenant should return 404
    response = await authenticated_async_client.get(f"/test-deps/test-nonexistent-tenant/{nonexistent_tenant_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND, f"Expected 404, got: {response.status_code}"


@pytest.mark.asyncio
async def test_invalid_tenant_id_format(
    setup_test_route: FastAPI,
    authenticated_async_client: AsyncClient
):
    """Test that an invalid tenant ID format returns 400."""
    # Use an invalid UUID format
    invalid_tenant_id = "not-a-uuid"
    
    # Should return 400 Bad Request for invalid UUID format for the no_bypass route
    response = await authenticated_async_client.get(f"/test-deps/test-nonexistent-tenant/{invalid_tenant_id}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400, got: {response.status_code}"


@pytest.mark.asyncio
async def test_missing_tenant_id_in_path(
    setup_test_route: FastAPI,
    authenticated_async_client: AsyncClient
):
    """Test that endpoints missing tenant_id in path return 400."""
    # Test all three dependency types
    response = await authenticated_async_client.get("/test-deps/test-missing-tenant-id-single")
    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400 for require_permission, got: {response.status_code}"
    
    response = await authenticated_async_client.get("/test-deps/test-missing-tenant-id-any")
    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400 for require_any_permission, got: {response.status_code}"
    
    response = await authenticated_async_client.get("/test-deps/test-missing-tenant-id-all")
    assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400 for require_all_permissions, got: {response.status_code}"


@pytest.mark.asyncio
async def test_require_all_permissions(
    setup_test_route: FastAPI,
    authenticated_async_client_user2: AsyncClient,
    db_session: AsyncSession
):
    """Test that require_all_permissions correctly requires all listed permissions."""
    assert hasattr(pytest, "tenant_id"), "Test tenant ID not set in conftest"
    assert hasattr(pytest, "user2_id"), "Test user2 ID not set in conftest"
    assert hasattr(pytest, "test_role_multiple_perms_id"), "Multiple permissions role ID not set"
    
    tenant_id = pytest.tenant_id
    user_id = pytest.user2_id
    role_id = pytest.test_role_multiple_perms_id
    
    # First test without the role assigned - should be 403
    response = await authenticated_async_client_user2.get(f"/test-deps/test-all-permissions/{tenant_id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN, f"Expected 403 without permissions, got: {response.status_code}"
    
    # Assign the multiple permissions role that has both VM_READ and TENANT_VIEW_USERS
    await user_service.assign_role_to_user_in_tenant(
        db_session,
        user_id=user_id,
        tenant_id=tenant_id,
        role_id=role_id
    )
    
    # Now they should have access
    response = await authenticated_async_client_user2.get(f"/test-deps/test-all-permissions/{tenant_id}")
    assert response.status_code == status.HTTP_200_OK, f"Access failed after assigning all required permissions: {response.text}"


@pytest.mark.asyncio
async def test_require_any_permission(
    setup_test_route: FastAPI,
    authenticated_async_client_user2: AsyncClient,
    db_session: AsyncSession
):
    """Test that require_any_permission correctly requires at least one of the listed permissions."""
    assert hasattr(pytest, "tenant_id"), "Test tenant ID not set in conftest"
    assert hasattr(pytest, "user2_id"), "Test user2 ID not set in conftest"
    assert hasattr(pytest, "test_role_single_perm_id"), "Single permission role ID not set"
    
    tenant_id = pytest.tenant_id
    user_id = pytest.user2_id
    role_id = pytest.test_role_single_perm_id  # Role with just VM_READ
    
    # Assign the single permission role to the user (VM_READ only)
    await user_service.assign_role_to_user_in_tenant(
        db_session,
        user_id=user_id,
        tenant_id=tenant_id,
        role_id=role_id
    )
    
    # They should have access since VM_READ is one of the listed permissions
    response = await authenticated_async_client_user2.get(f"/test-deps/test-any-permission/{tenant_id}")
    assert response.status_code == status.HTTP_200_OK, f"Access failed with VM_READ permission: {response.text}"
    
    # Remove the role assignment
    delete_stmt = user_tenant_roles_table.delete().where(
        and_(
            user_tenant_roles_table.c.user_id == user_id,
            user_tenant_roles_table.c.tenant_id == tenant_id,
            user_tenant_roles_table.c.role_id == role_id
        )
    )
    await db_session.execute(delete_stmt)
    await db_session.commit()
    
    # Create a role with only TENANT_VIEW_USERS (another permission in the any list)
    role_tenant_view = await role_service.create(
        db_session,
        obj_in={"name": f"Tenant View Role {uuid4()}", "tenant_id": tenant_id}
    )
    
    # Add TENANT_VIEW_USERS permission to the role
    tenant_view_users_perm = await permission_service.get_by_code(
        db_session,
        code=Permission.TENANT_VIEW_USERS.value
    )
    
    await role_service.add_permission_to_role(
        db_session,
        role_id=role_tenant_view.id,
        permission_id=tenant_view_users_perm.id
    )
    
    # Assign this role to the user
    await user_service.assign_role_to_user_in_tenant(
        db_session,
        user_id=user_id,
        tenant_id=tenant_id,
        role_id=role_tenant_view.id
    )
    
    # They should still have access with a different permission from the list
    response = await authenticated_async_client_user2.get(f"/test-deps/test-any-permission/{tenant_id}")
    assert response.status_code == status.HTTP_200_OK, f"Access failed with TENANT_VIEW_USERS permission: {response.text}" 