"""Base class for tool adapters."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result of executing a tool action."""
    success: bool
    action: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    url: str | None = None


class BaseTool(ABC):
    """Base class for all tool adapters.

    Each tool adapter wraps a provider API and exposes actions
    that can be invoked by the execution engine.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier (e.g., 'github', 'jira')."""

    @property
    @abstractmethod
    def supported_actions(self) -> list[str]:
        """List of action names this tool supports."""

    @abstractmethod
    async def execute(self, action: str, params: dict[str, Any], config: dict) -> ToolResult:
        """Execute an action with the given params and provider config.

        Args:
            action: The action name (e.g., 'create_issue', 'transition_issue')
            params: Action-specific parameters extracted from the delegation
            config: Provider credentials (token, domain, etc.)
        """

    def _validate_action(self, action: str) -> None:
        if action not in self.supported_actions:
            raise ValueError(
                f"Tool '{self.name}' does not support action '{action}'. "
                f"Supported: {self.supported_actions}"
            )
