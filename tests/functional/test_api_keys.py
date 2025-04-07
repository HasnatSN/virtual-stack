from uuid import uuid4

from fastapi import status
from httpx import AsyncClient
import pytest
import pytest_asyncio # Added for fixture decorator
from sqlalchemy.ext.asyncio import AsyncSession # Added for type hint

from virtualstack.schemas.iam.api_key import APIKeyScope
from virtualstack.models.iam import User

# Define the header name used for API key authentication
API_KEY_NAME = "X-API-Key" # TODO: Confirm this matches the actual implementation in deps.py


# Test data
TEST_API_KEY_BASE_NAME = f"pytest-key-{uuid4()}"
TEST_API_KEY_SUPERUSER = {
    "name": f"{TEST_API_KEY_BASE_NAME}-su",
    "description": "API Key created via pytest fixture (superuser)",
    "scope": APIKeyScope.GLOBAL.value,
}
TEST_API_KEY_USER2 = {
    "name": f"{TEST_API_KEY_BASE_NAME}-user2",
    "description": "API Key created via pytest fixture (user2)",
    "scope": APIKeyScope.GLOBAL.value,
}

# Mark tests as asyncio
pytestmark = pytest.mark.asyncio

# --- Fixtures ---

@pytest_asyncio.fixture(scope="function")
async def superuser_api_key(authenticated_async_client: AsyncClient) -> dict:
    """Fixture to create an API key as superuser and clean it up."""
    created_key_data = None
    key_id_to_delete = None
    print("\nCreating API key via superuser_api_key fixture...")
    try:
        response = await authenticated_async_client.post("/api/v1/api-keys/", json=TEST_API_KEY_SUPERUSER)
        response.raise_for_status()
        created_key_data = response.json()
        key_id_to_delete = created_key_data.get("id")
        print(f"Fixture created superuser API key ID: {key_id_to_delete}")
        yield created_key_data # Yield the full data including the raw key
    finally:
        if key_id_to_delete:
            print(f"Cleaning up superuser API key ID: {key_id_to_delete}")
            delete_response = await authenticated_async_client.delete(f"/api/v1/api-keys/{key_id_to_delete}")
            if delete_response.status_code not in [status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND]:
                print(f"WARNING: Failed to cleanup superuser API key {key_id_to_delete}. Status: {delete_response.status_code}, Text: {delete_response.text}")
        else:
             print("No superuser API key ID found to clean up in fixture.")


@pytest_asyncio.fixture(scope="function")
async def user2_api_key(authenticated_async_client_user2: AsyncClient) -> dict:
    """Fixture to create an API key as user2 and clean it up."""
    created_key_data = None
    key_id_to_delete = None
    print("\nCreating API key via user2_api_key fixture...")
    try:
        response = await authenticated_async_client_user2.post("/api/v1/api-keys/", json=TEST_API_KEY_USER2)
        response.raise_for_status()
        created_key_data = response.json()
        key_id_to_delete = created_key_data.get("id")
        print(f"Fixture created user2 API key ID: {key_id_to_delete}")
        yield created_key_data
    finally:
        if key_id_to_delete:
            print(f"Cleaning up user2 API key ID: {key_id_to_delete}")
            # Use the same client that created it to delete it
            delete_response = await authenticated_async_client_user2.delete(f"/api/v1/api-keys/{key_id_to_delete}")
            if delete_response.status_code not in [status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND]:
                print(f"WARNING: Failed to cleanup user2 API key {key_id_to_delete}. Status: {delete_response.status_code}, Text: {delete_response.text}")
        else:
             print("No user2 API key ID found to clean up in fixture.")


# --- Superuser Tests ---

# Use async def and await, use authenticated_async_client

async def test_create_api_key(authenticated_async_client: AsyncClient):
    """Test creating a new API key (superuser)."""
    # This test creates its own key and should clean it up
    key_data = {
        "name": f"test-create-key-{uuid4()}",
        "description": "API Key created directly in test_create_api_key",
        "scope": APIKeyScope.GLOBAL.value,
    }
    response = await authenticated_async_client.post("/api/v1/api-keys/", json=key_data)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["name"] == key_data["name"]
    assert data["description"] == key_data["description"]
    assert data["scope"] == key_data["scope"]
    assert "id" in data
    assert "key_prefix" in data
    assert "key" in data
    assert len(data["key"]) > 10
    assert data["key"].startswith("vsak_") # Updated prefix check

    # Cleanup the key created by this test
    key_id_to_delete = data["id"]
    print(f"Cleaning up key from test_create_api_key: {key_id_to_delete}")
    delete_response = await authenticated_async_client.delete(f"/api/v1/api-keys/{key_id_to_delete}")
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT, f"Cleanup failed: {delete_response.text}"


async def test_get_api_keys(authenticated_async_client: AsyncClient, superuser_api_key: dict):
    """Test retrieving API keys (should retrieve the one created by fixture)."""
    api_key_id = superuser_api_key["id"] # Get ID from fixture
    response = await authenticated_async_client.get("/api/v1/api-keys/")
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert isinstance(data, list)
    found = any(item["id"] == api_key_id for item in data if "id" in item)
    assert (
        found
    ), f"Fixture API key ID {api_key_id} not found in list: {data}"


async def test_get_api_key_by_id(authenticated_async_client: AsyncClient, superuser_api_key: dict):
    """Test getting a specific API key by ID using fixture."""
    api_key_id = superuser_api_key["id"] # Get ID from fixture

    response = await authenticated_async_client.get(f"/api/v1/api-keys/{api_key_id}")
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == api_key_id
    assert data["name"] == superuser_api_key["name"] # Compare against fixture data
    assert data["scope"] == superuser_api_key["scope"]


async def test_update_api_key(authenticated_async_client: AsyncClient, superuser_api_key: dict):
    """Test updating an API key using fixture."""
    api_key_id = superuser_api_key["id"] # Get ID from fixture
    update_data = {"description": "Updated via pytest fixture test"}

    response = await authenticated_async_client.put(
        f"/api/v1/api-keys/{api_key_id}", json=update_data
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == api_key_id
    assert data["description"] == update_data["description"]
    assert data["name"] == superuser_api_key["name"] # Name shouldn't change


async def test_delete_api_key(authenticated_async_client: AsyncClient):
    """Test deleting an API key (creates its own key)."""
    # This test creates its own key to delete, doesn't use the main fixture
    key_data = {
        "name": f"test-delete-key-{uuid4()}",
        "description": "API Key created directly in test_delete_api_key",
        "scope": APIKeyScope.GLOBAL.value,
    }
    create_response = await authenticated_async_client.post("/api/v1/api-keys/", json=key_data)
    assert create_response.status_code == status.HTTP_201_CREATED, create_response.text
    data = create_response.json()
    api_key_id = data["id"]


    response = await authenticated_async_client.delete(f"/api/v1/api-keys/{api_key_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text

    response_get = await authenticated_async_client.get(f"/api/v1/api-keys/{api_key_id}")
    assert response_get.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_api_key_not_found(authenticated_async_client: AsyncClient):
    """Test getting a non-existent API key by ID."""
    non_existent_uuid = uuid4()
    response = await authenticated_async_client.get(f"/api/v1/api-keys/{non_existent_uuid}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_api_key_not_found(authenticated_async_client: AsyncClient):
    """Test updating a non-existent API key."""
    non_existent_uuid = uuid4()
    update_data = {"description": "Updated Non-existent Key"}
    response = await authenticated_async_client.put(
        f"/api/v1/api-keys/{non_existent_uuid}", json=update_data
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_api_key_not_found(authenticated_async_client: AsyncClient):
    """Test deleting a non-existent API key."""
    non_existent_uuid = uuid4()
    response = await authenticated_async_client.delete(f"/api/v1/api-keys/{non_existent_uuid}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_api_key_forbidden(
    authenticated_async_client_user2: AsyncClient,
    superuser_api_key: dict # Create superuser's key
):
    """Test getting another user's (superuser's) API key (as non-superuser) - should fail 403."""
    api_key_id = superuser_api_key["id"] # Get superuser's key ID from fixture

    response = await authenticated_async_client_user2.get(f"/api/v1/api-keys/{api_key_id}")
    # Expect 403 Forbidden, not 404, as the key exists but user2 shouldn't access it
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
    assert "permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_update_api_key_forbidden(
    authenticated_async_client_user2: AsyncClient,
    superuser_api_key: dict # Create superuser's key
):
    """Test updating another user's (superuser's) API key (as non-superuser) - should fail 403."""
    api_key_id = superuser_api_key["id"] # Get superuser's key ID from fixture
    update_data = {"description": "Attempted Update by User 2"}

    response = await authenticated_async_client_user2.put(
        f"/api/v1/api-keys/{api_key_id}", json=update_data
    )
    # Expect 403 Forbidden
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
    assert "permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_api_key_forbidden(
    authenticated_async_client_user2: AsyncClient,
    superuser_api_key: dict # Create superuser's key
):
    """Test deleting another user's (superuser's) API key (as non-superuser) - should fail 403."""
    api_key_id = superuser_api_key["id"] # Get superuser's key ID from fixture

    response = await authenticated_async_client_user2.delete(f"/api/v1/api-keys/{api_key_id}")
    # Expect 403 Forbidden
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
    assert "permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_api_key_invalid_data(authenticated_async_client: AsyncClient):
    """Test creating an API key with missing required data (name)."""
    invalid_data = {"description": "Key without name"}
    response = await authenticated_async_client.post("/api/v1/api-keys/", json=invalid_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

# --- Regular User (User 2) Tests ---

# user2_key_data defined globally is now TEST_API_KEY_USER2

@pytest.mark.asyncio
async def test_user2_create_api_key(
    authenticated_async_client_user2: AsyncClient
) -> None:
    """Test user2 creating their own API key (creates and cleans up)."""
    key_data = { # Use local data specific to this test run
        "name": f"test-user2-create-{uuid4()}",
        "description": "API Key created directly in user2 create test",
        "scope": APIKeyScope.GLOBAL.value,
    }
    response = await authenticated_async_client_user2.post("/api/v1/api-keys/", json=key_data)
    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()
    assert data["name"] == key_data["name"]
    # Store user2's key ID for subsequent tests # REMOVED - No longer needed
    # pytest.user2_api_key_id = data["id"] # REMOVED
    # pytest.user2_api_key_value = data["key"] # REMOVED

    # Cleanup
    key_id_to_delete = data["id"]
    print(f"Cleaning up key from test_user2_create_api_key: {key_id_to_delete}")
    delete_response = await authenticated_async_client_user2.delete(f"/api/v1/api-keys/{key_id_to_delete}")
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT, f"Cleanup failed: {delete_response.text}"


@pytest.mark.asyncio
async def test_user2_list_own_api_keys(
    authenticated_async_client_user2: AsyncClient,
    user2_api_key: dict, # Use the user2 fixture
    superuser_api_key: dict # Also create the superuser key to ensure it's not listed
) -> None:
    """Test user2 listing their own API keys."""
    # assert hasattr(pytest, "user2_api_key_id"), "User2 API Key ID not set" # REMOVED
    user2_key_id = user2_api_key["id"]
    superuser_key_id = superuser_api_key["id"]

    response = await authenticated_async_client_user2.get("/api/v1/api-keys/")
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert isinstance(data, list)
    # Check if user2's key is present
    found_user2_key = any(item["id"] == user2_key_id for item in data)
    assert found_user2_key, "User2's fixture key not found in their list"
    # Check that the superuser's key is NOT present
    # if hasattr(pytest, "api_key_id"): # REMOVED
    found_superuser_key = any(item["id"] == superuser_key_id for item in data)
    assert not found_superuser_key, "Superuser's key found in user2's list"

@pytest.mark.asyncio
async def test_user2_get_own_api_key(
    authenticated_async_client_user2: AsyncClient,
    user2_api_key: dict # Use the user2 fixture
) -> None:
    """Test user2 getting their own API key by ID."""
    # assert hasattr(pytest, "user2_api_key_id"), "User2 API Key ID not set" # REMOVED
    key_id = user2_api_key["id"]
    response = await authenticated_async_client_user2.get(f"/api/v1/api-keys/{key_id}")
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == key_id
    assert data["name"] == user2_api_key["name"]

@pytest.mark.asyncio
async def test_user2_update_own_api_key(
    authenticated_async_client_user2: AsyncClient,
    user2_api_key: dict # Use the user2 fixture
) -> None:
    """Test user2 updating their own API key."""
    # assert hasattr(pytest, "user2_api_key_id"), "User2 API Key ID not set" # REMOVED
    key_id = user2_api_key["id"]
    update_data = {"description": "User 2 updated this fixture key"}
    response = await authenticated_async_client_user2.put(
        f"/api/v1/api-keys/{key_id}", json=update_data
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()
    assert data["id"] == key_id
    assert data["description"] == update_data["description"]

@pytest.mark.asyncio
async def test_user2_delete_own_api_key(
    authenticated_async_client_user2: AsyncClient
) -> None:
    """Test user2 deleting their own API key (creates its own)."""
    # assert hasattr(pytest, "user2_api_key_id"), "User2 API Key ID not set" # REMOVED
    # Create a key specifically for this test to delete
    key_data = {
        "name": f"test-user2-delete-{uuid4()}",
        "description": "API Key created by user2 for deletion test",
        "scope": APIKeyScope.GLOBAL.value,
    }
    create_response = await authenticated_async_client_user2.post("/api/v1/api-keys/", json=key_data)
    assert create_response.status_code == status.HTTP_201_CREATED, create_response.text
    data = create_response.json()
    key_id = data["id"]

    # Delete it
    response = await authenticated_async_client_user2.delete(f"/api/v1/api-keys/{key_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT, response.text
    # Verify deletion
    response_get = await authenticated_async_client_user2.get(f"/api/v1/api-keys/{key_id}")
    assert response_get.status_code == status.HTTP_404_NOT_FOUND

# --- Key Expiry Tests ---

from datetime import datetime, timedelta, timezone
import time

@pytest.mark.asyncio
async def test_api_key_expiry(
    authenticated_async_client: AsyncClient, # Superuser creates the key
    async_client: AsyncClient, # Use unauthenticated client for API key auth tests
) -> None:
    """Test API key authentication before and after expiry."""
    # 1. Create a key that expires in a short time (e.g., 5 seconds)
    expiry_time = datetime.now(timezone.utc) + timedelta(seconds=5)
    expiry_key_data = {
        "name": f"pytest-expiry-key-{uuid4()}",
        "scope": APIKeyScope.GLOBAL.value,
        "expires_at": expiry_time.isoformat() # Pass expiry time
    }
    response_create = await authenticated_async_client.post("/api/v1/api-keys/", json=expiry_key_data)
    assert response_create.status_code == status.HTTP_201_CREATED, response_create.text
    created_key_info = response_create.json()
    expiring_key_value = created_key_info["key"]
    expiring_key_id = created_key_info["id"]
    print(f"Created key {expiring_key_id} expiring at {expiry_time.isoformat()}")

    # 2. Test authentication with the key BEFORE expiry (e.g., get /users/me)
    headers_before = {API_KEY_NAME: expiring_key_value} # Use defined constant
    print(f"Testing auth with key {expiring_key_id} BEFORE expiry using header: {API_KEY_NAME}")
    # Use the base async_client (unauthenticated by default) and add the API key header
    response_before = await async_client.get("/api/v1/users/me", headers=headers_before)
    # Need to know which user the key belongs to. The fixture creates it as superuser.
    # Let's assert the correct user email is returned.
    assert response_before.status_code == status.HTTP_200_OK, f"Auth failed before expiry: {response_before.text}"
    user_data = response_before.json()
    # Assuming the superuser client used belongs to settings.TEST_USER_EMAIL
    from virtualstack.core.config import settings # Need settings for email
    assert user_data.get("email") == settings.TEST_USER_EMAIL
    print("Auth successful before expiry.")

    # 3. Wait until AFTER expiry
    wait_time = 6 # Wait 6 seconds to be safe
    print(f"Waiting {wait_time} seconds for key to expire...")
    time.sleep(wait_time)
    print("Wait complete.")

    # 4. Test authentication with the key AFTER expiry (should fail)
    headers_after = {API_KEY_NAME: expiring_key_value} # Use defined constant
    print(f"Testing auth with key {expiring_key_id} AFTER expiry using header: {API_KEY_NAME}")
    response_after = await async_client.get("/api/v1/users/me", headers=headers_after)
    # Expect 401 Unauthorized because the API key validation should fail
    assert response_after.status_code == status.HTTP_401_UNAUTHORIZED, f"Auth did not fail after expiry: {response_after.status_code}"
    # Check for the specific detail message we raise in deps.py
    assert "invalid or expired api key" in response_after.text.lower()
    print("Auth failed after expiry as expected.")

    # Cleanup: Delete the expired key (optional, but good practice)
    await authenticated_async_client.delete(f"/api/v1/api-keys/{expiring_key_id}")
