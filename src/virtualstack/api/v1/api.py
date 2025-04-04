from fastapi import APIRouter

from virtualstack.api.v1.endpoints import ( # noqa: F401
    api_keys,
    auth,
    invitations,
    roles,
    tenants,
    users,
    tenant_user_management, # Add the new router
    tenant_header_roles, # Add the new tenant header-based roles router
    tenant_header_users, # Add the new tenant header-based users router
)


api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Include user management endpoints with header-based tenant context (for frontend MVP)
api_router.include_router(tenant_header_users.router, prefix="/users", tags=["Users"])

# Include tenant management endpoints
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])

# Include API key management endpoints
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])

# Include roles endpoints with header-based tenant context (for frontend MVP)
api_router.include_router(tenant_header_roles.router, prefix="/roles", tags=["Roles"])

# Include invitation management endpoints
api_router.include_router(invitations.router, prefix="/invitations", tags=["Invitations"]) # Re-enabled invitations router

# LEGACY/DEPRECATED ENDPOINTS WITH PATH-BASED TENANT CONTEXT
# These will be removed in future versions - prefer the header-based tenant context endpoints
# Include the new router - note the prefix is different as tenant_id is part of the path
api_router.include_router(tenant_user_management.router, prefix="/tenants/{tenant_id}/users", tags=["Tenant User Management"])
api_router.include_router(roles.router, prefix="/tenants/{tenant_id}/roles", tags=["Tenant Role Management"])
