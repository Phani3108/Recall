"""Pytest configuration — test env before importing the app."""

from __future__ import annotations

import os

# Ensure settings pick test defaults (no Redis ping, etc.)
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://recall:recall@localhost:5432/recall_test",
    ),
)
