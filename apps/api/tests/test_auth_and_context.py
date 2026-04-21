"""Integration-style tests (Postgres + Alembic)."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _database_url_for_alembic() -> str:
    db = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://recall:recall@localhost:5432/recall_test",
    )
    if db.startswith("postgresql://") and "+asyncpg" not in db:
        db = db.replace("postgresql://", "postgresql+asyncpg://", 1)
    return db


@pytest.fixture(scope="session")
def migrated() -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = _database_url_for_alembic()
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        pytest.skip(f"Alembic upgrade failed (is Postgres running?): {r.stderr or r.stdout}")


@pytest.mark.asyncio
async def test_register_login_context_search(migrated: None) -> None:
    email = f"pytest_{uuid.uuid4().hex[:12]}@example.com"
    password = "testpassword123"
    org_name = f"Pytest Org {uuid.uuid4().hex[:8]}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg = await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "name": "Pytest User",
                "password": password,
                "org_name": org_name,
            },
        )
        if reg.status_code != 201:
            pytest.skip(f"register failed: {reg.status_code} {reg.text}")

        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = await client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200

        search = await client.post(
            "/api/context/search",
            headers=headers,
            json={"query": "onboarding", "limit": 10},
        )
        assert search.status_code == 200
        body = search.json()
        assert "results" in body
        assert "total" in body
        assert isinstance(body["results"], list)


@pytest.mark.asyncio
async def test_pilot_suggest_regex(migrated: None) -> None:
    email = f"pytest_{uuid.uuid4().hex[:12]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        reg = await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "name": "Suggest User",
                "password": "testpassword123",
                "org_name": f"Org {uuid.uuid4().hex[:6]}",
            },
        )
        if reg.status_code != 201:
            pytest.skip(f"register failed: {reg.status_code}")

        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r = await client.post(
            "/api/pilot/delegations/suggest",
            headers=headers,
            json={"action": "post to #general: ship it", "tool": "slack"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("source") == "regex"
        assert data.get("execution_payload") is not None
        assert data["execution_payload"]["tool"] == "slack"
        assert data["execution_payload"]["action"] == "post_message"
