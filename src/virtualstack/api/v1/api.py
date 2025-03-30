from fastapi import APIRouter

from virtualstack.api.v1.endpoints import auth, users, tenants, api_keys, roles

api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["auth"]
)

# Include user management endpoints
api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["users"]
)

# Include tenant management endpoints
api_router.include_router(
    tenants.router, 
    prefix="/tenants", 
    tags=["tenants"]
)

# Include API key management endpoints
api_router.include_router(
    api_keys.router, 
    prefix="/api-keys", 
    tags=["api-keys"]
)

# Include role management endpoints
api_router.include_router(
    roles.router, 
    prefix="/roles", 
    tags=["roles"]
)
