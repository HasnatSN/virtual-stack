from fastapi import APIRouter

from virtualstack.api.v1.endpoints import api_keys, auth, invitations, roles, tenants, users


api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Include user management endpoints
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Include tenant management endpoints
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])

# Include API key management endpoints
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"])

# Include role management endpoints
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])

# Include invitation management endpoints
api_router.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])
