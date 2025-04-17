#!/usr/bin/env bash
# Smoke-test: health, auth, user management endpoints
set -euo pipefail

# Start the dev server
echo "Starting dev server..."
bash scripts/run-without-reload.sh &  # Run server in background with logs
SERVER_PID=$!
sleep 5  # Wait for server startup and initial seeding

# 1. Health Check
echo "\n=== HEALTH CHECK ==="
curl -s http://localhost:8000/health | jq

# 2. Login -> get token
echo "\n=== LOGIN ==="
LOGIN_RESP=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@virtualstack.example&password=testpassword123!")
echo "$LOGIN_RESP" | jq
TOKEN=$(echo "$LOGIN_RESP" | jq -r '.access_token')
echo "Access Token: $TOKEN"

# 3. Get current user
echo "\n=== CURRENT USER (/users/me) ==="
curl -s http://localhost:8000/api/v1/users/me -H "Authorization: Bearer $TOKEN" | jq

# 4. List Tenants
echo "\n=== LIST TENANTS ==="
TENANTS=$(curl -s http://localhost:8000/api/v1/tenants -H "Authorization: Bearer $TOKEN")
echo "$TENANTS" | jq
TENANT_ID=$(echo "$TENANTS" | jq -r '.[0].id')
echo "Using Tenant ID: $TENANT_ID"

# 5. List Users in Tenant
echo "\n=== LIST USERS IN TENANT ==="
curl -s http://localhost:8000/api/v1/tenants/$TENANT_ID/users \
  -H "Authorization: Bearer $TOKEN" | jq

# 6. Cleanup
kill $SERVER_PID
echo "\nServer stopped (PID=$SERVER_PID)." 