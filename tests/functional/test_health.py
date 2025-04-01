import pytest
from httpx import AsyncClient
from fastapi import status


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test the root health check endpoint."""
    response = await async_client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "healthy"

    response = await async_client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "healthy"
