#!/usr/bin/env python3
"""
Test script to verify the functionality of the VirtualStack backend.
This script tests:
1. API access and health check
2. Authentication
3. Tenant creation
4. User creation
5. Role management
6. API Key functionality
7. Invitation functionality
"""

import httpx
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from pprint import pprint

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Test data
TEST_ADMIN = {
    "email": "admin@virtualstack.test",
    "password": "Password123!"
}

TEST_TENANT = {
    "name": "Test Tenant",
    "domain": "test.virtualstack.test",
    "company_name": "Virtual Stack, Inc."
}

TEST_USER = {
    "email": "user@test.virtualstack.test",
    "password": "Password123!",
    "first_name": "Test",
    "last_name": "User"
}

TEST_INVITATION = {
    "email": "invited@test.virtualstack.test",
    "expires_in_days": 7
}

TEST_ROLE = {
    "name": "Test Role",
    "description": "A test role"
}

TEST_API_KEY = {
    "name": "Test API Key",
    "description": "A test API key"
}

# Global state
state = {
    "access_token": None,
    "user_id": None,
    "tenant_id": None,
    "role_id": None,
    "api_key": None,
    "invitation_id": None,
    "invitation_link": None
}

async def request(method, path, json=None, params=None, token=None):
    """Make a request to the API and handle common error cases."""
    url = f"{BASE_URL}{path}"
    headers = {}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            url,
            json=json,
            params=params,
            headers=headers
        )
        
        try:
            if response.status_code >= 400:
                print(f"Error {response.status_code}: {response.text}")
                return None
            return response.json()
        except json.decoder.JSONDecodeError:
            if response.status_code < 400:
                return {"status": "success"}
            return None

async def test_health():
    """Test the health check endpoint."""
    print("\n🔍 Testing health check...")
    response = await request("GET", "/health")
    assert response is not None, "Health check failed"
    print("✅ Health check passed")

async def test_authentication():
    """Test authentication flow."""
    print("\n🔍 Testing authentication...")
    response = await request("POST", "/api/v1/auth/login", json={
        "username": TEST_ADMIN["email"],
        "password": TEST_ADMIN["password"],
    })
    
    assert response is not None, "Authentication failed"
    assert "access_token" in response, "No access token in response"
    
    state["access_token"] = response["access_token"]
    print("✅ Authentication passed")

async def test_tenant_creation():
    """Test creating a new tenant."""
    print("\n🔍 Testing tenant creation...")
    response = await request(
        "POST", 
        "/api/v1/tenants", 
        json=TEST_TENANT,
        token=state["access_token"]
    )
    
    assert response is not None, "Tenant creation failed"
    assert "id" in response, "No tenant ID in response"
    
    state["tenant_id"] = response["id"]
    print(f"✅ Tenant created with ID: {state['tenant_id']}")

async def test_user_creation():
    """Test creating a new user."""
    print("\n🔍 Testing user creation...")
    user_data = TEST_USER.copy()
    user_data["tenant_id"] = state["tenant_id"]
    
    response = await request(
        "POST", 
        "/api/v1/users", 
        json=user_data,
        token=state["access_token"]
    )
    
    assert response is not None, "User creation failed"
    assert "id" in response, "No user ID in response"
    
    state["user_id"] = response["id"]
    print(f"✅ User created with ID: {state['user_id']}")

async def test_role_creation():
    """Test creating a new role."""
    print("\n🔍 Testing role creation...")
    role_data = TEST_ROLE.copy()
    role_data["tenant_id"] = state["tenant_id"]
    
    response = await request(
        "POST", 
        "/api/v1/roles", 
        json=role_data,
        token=state["access_token"]
    )
    
    assert response is not None, "Role creation failed"
    assert "id" in response, "No role ID in response"
    
    state["role_id"] = response["id"]
    print(f"✅ Role created with ID: {state['role_id']}")

async def test_api_key_creation():
    """Test creating a new API key."""
    print("\n🔍 Testing API key creation...")
    api_key_data = TEST_API_KEY.copy()
    
    response = await request(
        "POST", 
        "/api/v1/api-keys", 
        json=api_key_data,
        token=state["access_token"]
    )
    
    assert response is not None, "API key creation failed"
    assert "key" in response, "No API key in response"
    
    state["api_key"] = response["key"]
    print(f"✅ API key created: {state['api_key'][:8]}...")

async def test_invitation_creation():
    """Test creating a new invitation."""
    print("\n🔍 Testing invitation creation...")
    invitation_data = TEST_INVITATION.copy()
    invitation_data["role_id"] = state["role_id"]
    
    response = await request(
        "POST", 
        "/api/v1/invitations", 
        json=invitation_data,
        token=state["access_token"]
    )
    
    assert response is not None, "Invitation creation failed"
    assert "id" in response, "No invitation ID in response"
    assert "invitation_link" in response, "No invitation link in response"
    
    state["invitation_id"] = response["id"]
    state["invitation_link"] = response["invitation_link"]
    print(f"✅ Invitation created with ID: {state['invitation_id']}")
    print(f"✅ Invitation link: {state['invitation_link']}")

async def test_verify_invitation():
    """Test verifying an invitation token."""
    print("\n🔍 Testing invitation verification...")
    # Extract token from invitation link
    token = state["invitation_link"].split("token=")[1]
    
    response = await request(
        "POST", 
        "/api/v1/invitations/verify", 
        json={"token": token}
    )
    
    assert response is not None, "Invitation verification failed"
    assert response["valid"] is True, "Invitation token is not valid"
    assert response["email"] == TEST_INVITATION["email"], "Wrong email in invitation"
    
    print(f"✅ Invitation verified for: {response['email']}")

async def test_get_invitation():
    """Test getting invitation details."""
    print("\n🔍 Testing getting invitation details...")
    
    response = await request(
        "GET", 
        f"/api/v1/invitations/{state['invitation_id']}", 
        token=state["access_token"]
    )
    
    assert response is not None, "Getting invitation failed"
    assert response["id"] == state["invitation_id"], "Wrong invitation ID"
    assert response["email"] == TEST_INVITATION["email"], "Wrong email in invitation"
    
    print(f"✅ Retrieved invitation details for: {response['email']}")

async def test_list_invitations():
    """Test listing invitations."""
    print("\n🔍 Testing listing invitations...")
    
    response = await request(
        "GET", 
        "/api/v1/invitations", 
        token=state["access_token"]
    )
    
    assert response is not None, "Listing invitations failed"
    assert isinstance(response, list), "Response is not a list"
    assert len(response) > 0, "No invitations found"
    
    print(f"✅ Listed {len(response)} invitations")

async def main():
    """Run all tests in sequence."""
    print("🚀 Starting API functionality tests...\n")
    
    try:
        await test_health()
        await test_authentication()
        await test_tenant_creation()
        await test_user_creation()
        await test_role_creation()
        await test_api_key_creation()
        await test_invitation_creation()
        await test_verify_invitation()
        await test_get_invitation()
        await test_list_invitations()
        
        print("\n✅ All tests passed!")
        print("\nTest state:")
        for key, value in state.items():
            if key == "access_token" and value:
                print(f"  {key}: {value[:15]}...")
            elif key == "api_key" and value:
                print(f"  {key}: {value[:8]}...")
            else:
                print(f"  {key}: {value}")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 