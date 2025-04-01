from typing import Callable
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from virtualstack.services.iam import tenant_service


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware to handle tenant context in multi-tenancy application.

    This middleware extracts the tenant ID from the X-Tenant-ID header,
    validates it against the database, and adds the tenant information
    to the request state for access in route handlers.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Extract tenant ID from header
        tenant_id_str = request.headers.get("X-Tenant-ID")

        # If tenant ID is provided, validate and set in request state
        if tenant_id_str:
            try:
                # Validate UUID format
                tenant_id = UUID(tenant_id_str)

                # Get tenant from database
                tenant = await tenant_service.get(tenant_id)

                if not tenant:
                    return JSONResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        content={"detail": "Tenant not found"},
                    )

                if not tenant.is_active:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "Tenant is inactive"},
                    )

                # Set tenant in request state
                request.state.tenant_id = tenant_id
                request.state.tenant = tenant

            except ValueError:
                # Invalid UUID format
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid tenant ID format. Must be a valid UUID."},
                )

        # Continue processing the request
        return await call_next(request)


def setup_middleware(app: FastAPI) -> None:
    """Add custom middleware to the FastAPI application."""
    app.add_middleware(TenantContextMiddleware)
