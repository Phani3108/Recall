"""Unit tests for Pilot execution payload resolution."""

from app.services.execution_engine import (
    build_execution_payload_best_effort,
    normalize_execution_payload,
    parse_delegation_action,
)


def test_parse_github_close() -> None:
    parsed = parse_delegation_action("close #42 in org/repo", tool_hint="github")
    assert parsed is not None
    assert parsed["tool"] == "github"
    assert parsed["action"] == "close_issue"
    assert parsed["params"]["issue_number"] == 42
    assert parsed["params"]["repo"] == "org/repo"


def test_normalize_valid_payload() -> None:
    raw = {"tool": "slack", "action": "post_message", "params": {"channel": "#eng", "text": "hi"}}
    out = normalize_execution_payload(raw)
    assert out == raw


def test_normalize_rejects_unknown_tool() -> None:
    assert normalize_execution_payload({"tool": "unknown", "action": "x", "params": {}}) is None


def test_build_best_effort_from_nl() -> None:
    payload = build_execution_payload_best_effort(
        "post to #general: standup done",
        "slack",
    )
    assert payload is not None
    assert payload["tool"] == "slack"
    assert payload["action"] == "post_message"
