"""Smoke tests for public endpoints."""

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_ok() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["environment"] == "test"
