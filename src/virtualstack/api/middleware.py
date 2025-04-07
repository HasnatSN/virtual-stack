from typing import Callable
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Remove tenant_service import as we won't call it here
# from virtualstack.services.iam import tenant_service


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware to handle tenant context in multi-tenancy application.

    This middleware extracts the tenant ID from the X-Tenant-ID header,
    validates its UUID format, and adds the tenant_id to the request state
    for access in route handlers or dependencies.
    Tenant existence and status validation should be handled later in the request lifecycle
    by a dependency that has access to a database session.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Extract tenant ID from header
        tenant_id_str = request.headers.get("X-Tenant-ID")
        request.state.tenant_id = None # Initialize state

        # If tenant ID is provided, validate and set in request state
        if tenant_id_str:
            try:
                # Validate UUID format
                tenant_id = UUID(tenant_id_str)
                # Store the validated UUID in the request state
                request.state.tenant_id = tenant_id
                # Removed database lookup and tenant object storage
                # request.state.tenant = tenant # Removed

            except ValueError:
                # Invalid UUID format
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid tenant ID format. Must be a valid UUID."},
                )
            # Removed tenant existence and activity checks

        # Continue processing the request
        response = await call_next(request)
        return response


def setup_middleware(app: FastAPI) -> None:
    """Add custom middleware to the FastAPI application."""
    app.add_middleware(TenantContextMiddleware)
