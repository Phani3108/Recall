"""Unit tests for GitHub tool adapter with mocked HTTP."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.tool_adapters.github import GitHubTool


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers=None, json=None):
        assert "api.github.com/repos/acme/api/issues" in url
        assert headers and "Bearer" in headers["Authorization"]
        assert json["title"] == "Bug from Recall"

        class _Resp:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {
                    "number": 7,
                    "id": 9001,
                    "title": "Bug from Recall",
                    "html_url": "https://github.com/acme/api/issues/7",
                }

        return _Resp()


@pytest.mark.asyncio
async def test_create_issue_posts_to_github() -> None:
    with patch("app.services.tool_adapters.github.httpx.AsyncClient", _FakeAsyncClient):
        tool = GitHubTool()
        result = await tool.execute(
            "create_issue",
            {"repo": "acme/api", "title": "Bug from Recall", "body": "Details"},
            {"token": "ghs_test"},
        )

    assert result.success is True
    assert result.action == "create_issue"
    assert result.data and result.data["number"] == 7
    assert result.url == "https://github.com/acme/api/issues/7"
