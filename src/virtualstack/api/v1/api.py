from fastapi import APIRouter

from virtualstack.api.v1.endpoints import ( # noqa: F401
    api_keys,
    auth,
    invitations,
    roles,
    tenants,
    users, # Keep import for now, might need /users/me later
    tenant_user_management,
)


api_router = APIRouter()

# === Global Endpoints ===

# Authentication (not tenant-specific)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Current User Info (not tenant-specific)
# TODO: Decide if /users/me should remain top-level or move elsewhere.
# Keep users.router included ONLY for /me for now.
api_router.include_router(users.router, prefix="/users", tags=["Users (Self)"])

# Tenant Listing (accessible by user, not specific tenant context)
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants (Global)"])

# API Key Management (assuming global for user for now)
# TODO: Confirm if API Keys should be tenant-scoped?
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])

# Invitation Management (potentially global or needs tenant scoping review)
# TODO: Review invitation scoping.
api_router.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])

# Global Permissions List
# TODO: Move the GET /permissions endpoint to a dedicated permissions router?
# For now, it's included via the tenant-scoped roles router below, which is confusing.

# === Tenant-Scoped Endpoints ===

# Mount user management endpoints under tenant context
# This now includes list, create, get, update, delete for users within a tenant
api_router.include_router(
    tenant_user_management.router, # Assuming list users etc. are moved here
    prefix="/tenants/{tenant_id}/users",
    tags=["Tenant User Management"]
)

# Mount role management endpoints under tenant context
# This includes list, create, get, update, delete roles within a tenant,
# role assignment, and the global permission list (which should move).
api_router.include_router(
    roles.router,
    prefix="/tenants/{tenant_id}/roles",
    tags=["Tenant Role Management"]
)

# Removed duplicate/incorrect mountings:
# api_router.include_router(users.router, prefix="/users", tags=["Users"]) # Removed global user management
# api_router.include_router(roles.router, prefix="/roles", tags=["Roles"]) # Removed global role management
