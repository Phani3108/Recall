"""Tool adapters — execute actions against external provider APIs.

Each adapter exposes a set of actions (e.g., create_issue, transition_issue)
that the execution engine can invoke on behalf of approved delegations.
"""

from app.services.tool_adapters.github import GitHubTool
from app.services.tool_adapters.jira import JiraTool
from app.services.tool_adapters.confluence import ConfluenceTool
from app.services.tool_adapters.slack import SlackTool

# Registry mapping tool names to adapter classes
TOOL_REGISTRY: dict[str, type] = {
    "github": GitHubTool,
    "jira": JiraTool,
    "confluence": ConfluenceTool,
    "slack": SlackTool,
}

__all__ = ["TOOL_REGISTRY", "GitHubTool", "JiraTool", "ConfluenceTool", "SlackTool"]
