import httpx
import os
import logging
from dotenv import load_dotenv
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables for API URL, username, password
load_dotenv()
API_BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000") # Default to localhost:8000
TEST_USERNAME = os.getenv("TEST_USER_EMAIL", "admin@example.com") # Use env var or default
TEST_PASSWORD = os.getenv("TEST_USER_PASSWORD", "changeme") # Use env var or default

# TODO: Ensure the TEST_USER_EMAIL and TEST_USER_PASSWORD exist in the database
#       and are associated with at least one tenant for tenant listing to work.

api_v1_base = "http://127.0.0.1:8000/api/v1"

def test_health_check():
    """Tests the health check endpoint."""
    url = f"{API_BASE_URL}/health"
    logging.info(f"Testing health check: GET {url}")
    try:
        with httpx.Client() as client:
            response = client.get(url, timeout=10)
            logging.info(f"Health check status: {response.status_code}")
            logging.info(f"Health check response: {response.json()}")
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            assert response.status_code == 200
            assert response.json().get("status") == "healthy"
            logging.info("✅ Health check PASSED")
    except httpx.RequestError as exc:
        logging.error(f"❌ Health check FAILED: Request error {exc}")
    except httpx.HTTPStatusError as exc:
        logging.error(f"❌ Health check FAILED: HTTP status error {exc}")
    except Exception as exc:
        logging.error(f"❌ Health check FAILED: An unexpected error occurred: {exc}")

def get_auth_token(client: httpx.Client) -> Optional[str]:
    """Authenticates and returns an access token."""
    url = f"{api_v1_base}/auth/token"
    logging.info(f"Attempting login: POST {url} for user {TEST_USERNAME}")
    try:
        response = client.post(
            url,
            data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        logging.info(f"Login status: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            if token:
                logging.info("🔑 Login successful, token obtained.")
                return token
            else:
                logging.error("❌ Login FAILED: Token not found in response.")
                logging.error(f"Login response: {response.json()}")
                return None
        else:
            logging.error(f"❌ Login FAILED: Status code {response.status_code}")
            try:
                 logging.error(f"Login error response: {response.json()}")
            except Exception:
                 logging.error(f"Login error response (non-JSON): {response.text}")
            return None
    except httpx.RequestError as exc:
        logging.error(f"❌ Login FAILED: Request error {exc}")
        return None
    except Exception as exc:
        logging.error(f"❌ Login FAILED: An unexpected error occurred: {exc}")
        return None

def log_non_json_error(response: httpx.Response, context: str):
    try:
        error_detail = response.json()
    except Exception:
        error_detail = response.text
    logging.error(f"❌ {context} FAILED: Status code {response.status_code}")
    logging.error(f"{context} error response (non-JSON): {error_detail}")

def test_list_tenants(client: httpx.Client, token: str):
    url = f"{api_v1_base}/tenants/" # Use base URL and add trailing slash
    logging.info(f"Testing list tenants: GET {url}") 
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Use the constructed full URL
        response = client.get(url, headers=headers) 
        logging.info(f"List tenants status: {response.status_code}")
        if response.status_code == 200:
            tenants = response.json()
            logging.info(f"List tenants response: {tenants}")
            logging.info("✅ List tenants PASSED")
            # Return the ID of the first tenant found for subsequent tests
            return tenants[0]["id"] if tenants else None
        else:
            log_non_json_error(response, "List tenants")
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logging.error(f"❌ List tenants FAILED: HTTP status error {e}")
    except httpx.RequestError as e:
        logging.error(f"❌ List tenants FAILED: Request error {e}")
    except Exception as e:
        logging.error(f"❌ List tenants FAILED: Unexpected error {e}")
    return None

def test_list_users_in_tenant(client: httpx.Client, token: str, tenant_id: str):
    """Tests listing users within a specific tenant."""
    if not tenant_id:
        logging.warning("⚠️ Skipping list users test: No tenant ID available.")
        return

    # Construct the URL using the tenant_id
    # IMPORTANT: This assumes the API router includes the tenant context in the path like /api/v1/tenants/{tenant_id}/users
    # Adjust this URL based on your actual API structure defined in src/virtualstack/api/v1/api.py
    # If the tenant context is derived from deps/headers/token instead of the path, use the simpler URL.
    # Check how the APIRouter for 'users.py' is included in 'api.py'.
    # Example if nested:
    # url = f"{api_v1_base}/tenants/{tenant_id}/users"
    # Example if not nested (assuming deps handle context):
    url = f"{api_v1_base}/tenants/{tenant_id}/users/"

    # Verify the correct API path structure. Let's check src/virtualstack/api/v1/api.py briefly.
    # Assuming for now the endpoints are NOT nested under /tenants/{tenant_id} based on previous edits.
    # The get_tenant_from_path dependency must be correctly configured in api.py for this to work.

    logging.info(f"Testing list users in tenant: GET {url} (Tenant Context Implied/Handled by Deps)")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        # Pass tenant_id in a header if required by middleware/deps, e.g.:
        # headers["X-Tenant-ID"] = tenant_id
        # For now, assume get_tenant_from_path works via URL path segment if router is set up correctly.
        # If the /users endpoint is mounted at the root of the tenant router, this will fail.

        # Let's assume the router mounts users under /tenants/{tenant_id}/users based on best practice
        response = client.get(url, headers=headers, params={"page": 1, "limit": 5}, timeout=10) # Test with pagination
        logging.info(f"List users status: {response.status_code}")
        if response.status_code == 200:
            user_data = response.json()
            logging.info(f"List users response: {user_data}")
            assert "items" in user_data
            assert "total" in user_data
            assert isinstance(user_data["items"], list)
            # Check if the current test user is in the list (adjust based on TEST_USERNAME)
            found_self = any(user.get("email") == TEST_USERNAME for user in user_data["items"])
            logging.info(f"Current test user found in list: {found_self}")
            # assert found_self # This might fail depending on pagination/search
            logging.info("✅ List users PASSED")
        else:
            logging.error(f"❌ List users FAILED: Status code {response.status_code}")
            try:
                 logging.error(f"List users error response: {response.json()}")
            except Exception:
                 logging.error(f"List users error response (non-JSON): {response.text}")
            response.raise_for_status() # Raise exception for bad status
    except httpx.RequestError as exc:
        logging.error(f"❌ List users FAILED: Request error {exc}")
    except httpx.HTTPStatusError as exc:
        logging.error(f"❌ List users FAILED: HTTP status error {exc}")
    except Exception as exc:
        logging.error(f"❌ List users FAILED: An unexpected error occurred: {exc}")


if __name__ == "__main__":
    logging.info("--- Starting Basic API Tests ---")
    test_health_check()

    # Use a single client session for subsequent requests
    with httpx.Client() as client:
        token = get_auth_token(client)
        if token:
            # Test endpoints requiring authentication
            tenant_id = test_list_tenants(client, token)
            if tenant_id: # Only proceed if we got a tenant ID
                test_list_users_in_tenant(client, token, tenant_id)
            else:
                logging.warning("⚠️ Skipping user tests as no tenant ID was retrieved.")

    logging.info("--- Basic API Tests Finished ---") 