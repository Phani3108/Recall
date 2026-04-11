"""Integration sync service — pulls data from connected providers into context entities.

Each provider has a sync function that:
1. Validates credentials via a test API call
2. Fetches recent data (repos, issues, messages, pages, etc.)
3. Returns a list of entity dicts for upserting into context_entities
4. Indexes entities into Weaviate for hybrid search
"""

import logging
import uuid
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContextEntity, EntityType

logger = logging.getLogger(__name__)

# ── Provider field definitions (exposed via API for frontend) ──

PROVIDER_FIELDS: dict[str, list[dict[str, Any]]] = {
    "github": [
        {"key": "token", "label": "Personal Access Token", "placeholder": "ghp_xxxxxxxxxxxx"},
    ],
    "slack": [
        {"key": "token", "label": "Bot OAuth Token", "placeholder": "xoxb-xxxxxxxxxxxx"},
    ],
    "google": [
        {"key": "token", "label": "OAuth Access Token or API Key", "placeholder": "ya29.xxx or AIza..."},
    ],
    "notion": [
        {"key": "token", "label": "Internal Integration Token", "placeholder": "ntn_xxxxxxxxxxxx"},
    ],
    "jira": [
        {"key": "email", "label": "Atlassian Email", "placeholder": "you@company.com"},
        {"key": "token", "label": "API Token", "placeholder": "ATATT3xFfGF0..."},
        {"key": "domain", "label": "Jira Domain", "placeholder": "yourcompany.atlassian.net"},
    ],
    "linear": [
        {"key": "token", "label": "API Key", "placeholder": "lin_api_xxxxxxxxxxxx"},
    ],
    "confluence": [
        {"key": "email", "label": "Atlassian Email", "placeholder": "you@company.com"},
        {"key": "token", "label": "API Token", "placeholder": "ATATT3xFfGF0..."},
        {"key": "domain", "label": "Confluence Domain", "placeholder": "yourcompany.atlassian.net"},
    ],
    "gitlab": [
        {"key": "token", "label": "Personal Access Token", "placeholder": "glpat-xxxxxxxxxxxx"},
        {"key": "domain", "label": "GitLab Domain (optional)", "placeholder": "gitlab.com"},
    ],
    "microsoft365": [
        {"key": "token", "label": "Microsoft Graph Access Token", "placeholder": "eyJ0eX..."},
    ],
    "dropbox": [
        {"key": "token", "label": "Access Token", "placeholder": "sl.xxxxx"},
    ],
    "zoom": [
        {"key": "token", "label": "Access Token", "placeholder": "eyJ0eX..."},
    ],
    "figma": [
        {"key": "token", "label": "Personal Access Token", "placeholder": "figd_xxxxxxxxxxxx"},
    ],
    "asana": [
        {"key": "token", "label": "Personal Access Token", "placeholder": "1/12345:abcdef..."},
    ],
    "hubspot": [
        {"key": "token", "label": "Private App Token", "placeholder": "pat-na1-xxxxxxxxxxxx"},
    ],
    "claude": [
        {"key": "token", "label": "Anthropic API Key", "placeholder": "sk-ant-api03-xxxxxxxxxxxx"},
    ],
}

PROVIDER_HELP_URLS: dict[str, str] = {
    "github": "https://github.com/settings/tokens",
    "slack": "https://api.slack.com/apps",
    "google": "https://console.cloud.google.com/apis/credentials",
    "notion": "https://www.notion.so/my-integrations",
    "jira": "https://id.atlassian.com/manage-profile/security/api-tokens",
    "linear": "https://linear.app/settings/api",
    "confluence": "https://id.atlassian.com/manage-profile/security/api-tokens",
    "gitlab": "https://gitlab.com/-/user_settings/personal_access_tokens",
    "microsoft365": "https://developer.microsoft.com/en-us/graph/graph-explorer",
    "dropbox": "https://www.dropbox.com/developers/apps",
    "zoom": "https://marketplace.zoom.us/develop/create",
    "figma": "https://www.figma.com/developers/api#access-tokens",
    "asana": "https://app.asana.com/0/my-apps",
    "hubspot": "https://developers.hubspot.com/docs/api/private-apps",
    "claude": "https://console.anthropic.com/settings/keys",
}


# ── Core sync logic ──


async def validate_and_sync(
    provider: str,
    config: dict,
    org_id: uuid.UUID,
    integration_id: uuid.UUID,
    db: AsyncSession,
    since: datetime | None = None,
) -> dict:
    """Validate credentials and sync data from a provider.

    Args:
        since: If provided, only fetch items updated after this timestamp (incremental sync).

    Returns: {"status": "ok"|"error", "synced": int, "indexed": int, "error": str|None}
    """
    syncer = _SYNCERS.get(provider)
    if not syncer:
        return {"status": "error", "synced": 0, "indexed": 0, "error": f"No syncer for {provider}"}

    try:
        entities = await syncer(config, since=since)
        count = await _upsert_entities(entities, org_id, integration_id, db)

        # Index into Weaviate for hybrid search (best-effort, don't fail sync)
        indexed = await _index_entities_to_weaviate(entities, org_id, integration_id, db)

        # Build entity relationships for the knowledge graph (best-effort)
        relations = await _build_entity_relations(entities, org_id, db)

        return {"status": "ok", "synced": count, "indexed": indexed, "relations": relations, "error": None}
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code in (401, 403):
            return {"status": "error", "synced": 0, "indexed": 0, "error": "Invalid or expired credentials"}
        return {"status": "error", "synced": 0, "indexed": 0, "error": f"Provider API error ({code})"}
    except ValueError as e:
        return {"status": "error", "synced": 0, "indexed": 0, "error": str(e)}
    except Exception as e:
        logger.error("Sync failed for %s: %s", provider, e, exc_info=True)
        return {"status": "error", "synced": 0, "indexed": 0, "error": f"Sync failed: {type(e).__name__}"}


async def _upsert_entities(
    entities: list[dict],
    org_id: uuid.UUID,
    integration_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    """Insert or update context entities from synced data."""
    count = 0
    for e in entities:
        result = await db.execute(
            select(ContextEntity).where(
                ContextEntity.org_id == org_id,
                ContextEntity.source_id == e["source_id"],
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.title = e["title"]
            existing.content = e.get("content", "")
            existing.source_url = e.get("source_url")
            existing.extra_data = e.get("extra_data", {})
        else:
            db.add(ContextEntity(
                org_id=org_id,
                entity_type=EntityType(e["entity_type"]),
                title=e["title"],
                content=e.get("content", ""),
                source_integration_id=integration_id,
                source_url=e.get("source_url"),
                source_id=e["source_id"],
                extra_data=e.get("extra_data", {}),
                access_everyone=True,
            ))
        count += 1
    await db.flush()
    return count


async def _index_entities_to_weaviate(
    entities: list[dict],
    org_id: uuid.UUID,
    integration_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    """Best-effort index synced entities into Weaviate for hybrid search."""
    try:
        from app.services.context_engine import index_entity, ensure_collection_exists
        await ensure_collection_exists()
    except Exception:
        logger.warning("Weaviate unavailable, skipping vector indexing")
        return 0

    indexed = 0
    for e in entities:
        try:
            # Look up the entity we just upserted to get its UUID
            result = await db.execute(
                select(ContextEntity).where(
                    ContextEntity.org_id == org_id,
                    ContextEntity.source_id == e["source_id"],
                )
            )
            entity = result.scalar_one_or_none()
            if not entity:
                continue

            vector_ids = await index_entity(
                entity_id=entity.id,
                org_id=org_id,
                entity_type=e["entity_type"],
                title=e["title"],
                content=e.get("content", ""),
                source_integration=e.get("extra_data", {}).get("source_integration", ""),
                source_url=e.get("source_url"),
                access_everyone=True,
            )
            if vector_ids:
                entity.vector_id = vector_ids[0]
                indexed += 1
        except Exception:
            logger.debug("Failed to index entity %s", e.get("source_id"), exc_info=True)
            continue

    await db.flush()
    return indexed


async def _build_entity_relations(
    entities: list[dict],
    org_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    """Best-effort build entity relationships for the knowledge graph."""
    try:
        from app.services.graph_builder import build_relations_for_entity
    except Exception:
        logger.warning("Graph builder unavailable, skipping relation extraction")
        return 0

    relations = 0
    for e in entities:
        try:
            result = await db.execute(
                select(ContextEntity).where(
                    ContextEntity.org_id == org_id,
                    ContextEntity.source_id == e["source_id"],
                )
            )
            entity = result.scalar_one_or_none()
            if entity:
                count = await build_relations_for_entity(entity, db)
                relations += count
        except Exception:
            logger.debug("Failed to build relations for %s", e.get("source_id"), exc_info=True)
            continue

    return relations


# ── Provider implementations ──


async def _sync_github(config: dict, since: datetime | None = None) -> list[dict]:
    token = config["token"]
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    entities: list[dict] = []
    since_param = f"&since={since.isoformat()}" if since else ""

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Validate + fetch repos
        resp = await client.get(
            "https://api.github.com/user/repos?per_page=30&sort=updated", headers=headers
        )
        resp.raise_for_status()
        repos = resp.json()

        for repo in repos:
            entities.append({
                "source_id": f"github:repo:{repo['full_name']}",
                "entity_type": "document",
                "title": repo["full_name"],
                "content": (
                    f"{repo.get('description') or 'No description'}\n\n"
                    f"Language: {repo.get('language') or 'Unknown'} | "
                    f"Stars: {repo.get('stargazers_count', 0)} | "
                    f"Forks: {repo.get('forks_count', 0)} | "
                    f"Updated: {repo.get('updated_at', '')[:10]}"
                ),
                "source_url": repo["html_url"],
                "extra_data": {"source_integration": "github", "type": "repository"},
            })

        # Recent issues/PRs from top 5 active repos
        for repo in repos[:5]:
            try:
                ir = await client.get(
                    f"https://api.github.com/repos/{repo['full_name']}/issues"
                    f"?state=all&per_page=10&sort=updated{since_param}",
                    headers=headers,
                )
                ir.raise_for_status()
                for issue in ir.json():
                    kind = "pr" if "pull_request" in issue else "issue"
                    entities.append({
                        "source_id": f"github:{kind}:{repo['full_name']}#{issue['number']}",
                        "entity_type": "task",
                        "title": f"[{repo['name']}] #{issue['number']} {issue['title']}",
                        "content": (issue.get("body") or "")[:2000],
                        "source_url": issue["html_url"],
                        "extra_data": {
                            "source_integration": "github", "type": kind,
                            "state": issue["state"],
                            "labels": [l["name"] for l in issue.get("labels", [])],
                        },
                    })
            except Exception:
                continue

    return entities


async def _sync_slack(config: dict, since: datetime | None = None) -> list[dict]:
    token = config["token"]
    headers = {"Authorization": f"Bearer {token}"}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Validate + list channels
        resp = await client.get(
            "https://slack.com/api/conversations.list?types=public_channel&limit=20",
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise ValueError(f"Slack API error: {data.get('error', 'unknown')}")

        channels = data.get("channels", [])
        for ch in channels:
            entities.append({
                "source_id": f"slack:channel:{ch['id']}",
                "entity_type": "thread",
                "title": f"#{ch['name']}",
                "content": ch.get("purpose", {}).get("value", "") or ch.get("topic", {}).get("value", ""),
                "source_url": f"https://app.slack.com/client/{ch.get('shared_team_id', '')}/{ch['id']}",
                "extra_data": {"source_integration": "slack", "type": "channel", "members": ch.get("num_members", 0)},
            })

        # Recent messages from top channels
        for ch in channels[:5]:
            try:
                hr = await client.get(
                    f"https://slack.com/api/conversations.history?channel={ch['id']}&limit=10",
                    headers=headers,
                )
                hr.raise_for_status()
                for msg in hr.json().get("messages", []):
                    if msg.get("subtype"):
                        continue
                    entities.append({
                        "source_id": f"slack:msg:{ch['id']}:{msg['ts']}",
                        "entity_type": "message",
                        "title": f"#{ch['name']} message",
                        "content": msg.get("text", "")[:2000],
                        "source_url": f"https://app.slack.com/client/{ch.get('shared_team_id', '')}/{ch['id']}",
                        "extra_data": {"source_integration": "slack", "type": "message", "channel": ch["name"]},
                    })
            except Exception:
                continue

    return entities


async def _sync_notion(config: dict, since: datetime | None = None) -> list[dict]:
    token = config["token"]
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.notion.com/v1/search",
            headers=headers,
            json={"page_size": 50, "sort": {"direction": "descending", "timestamp": "last_edited_time"}},
        )
        resp.raise_for_status()

        for item in resp.json().get("results", []):
            obj_type = item.get("object", "")
            title_parts = []

            if obj_type == "page":
                props = item.get("properties", {})
                for _key, val in props.items():
                    if val.get("type") == "title":
                        title_parts = [t.get("plain_text", "") for t in val.get("title", [])]
                        break
            elif obj_type == "database":
                title_parts = [t.get("plain_text", "") for t in item.get("title", [])]

            title = "".join(title_parts) or "Untitled"
            page_url = item.get("url", "")

            entities.append({
                "source_id": f"notion:{obj_type}:{item['id']}",
                "entity_type": "document",
                "title": f"[Notion] {title}",
                "content": f"Type: {obj_type}\nLast edited: {item.get('last_edited_time', '')[:10]}",
                "source_url": page_url,
                "extra_data": {"source_integration": "notion", "type": obj_type},
            })

    return entities


async def _sync_jira(config: dict, since: datetime | None = None) -> list[dict]:
    import base64
    email, token, domain = config["email"], config["token"], config["domain"]
    domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
    entities: list[dict] = []

    # Build JQL with optional since filter
    jql = "ORDER+BY+updated+DESC"
    if since:
        jql = f"updated+>=+'{since.strftime('%Y-%m-%d+%H:%M')}'+ORDER+BY+updated+DESC"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch issues with expanded fields
        resp = await client.get(
            f"https://{domain}/rest/api/3/search?jql={jql}"
            f"&maxResults=50&fields=summary,description,status,priority,assignee,comment,sprint,labels,issuetype,project",
            headers=headers,
        )
        resp.raise_for_status()

        for issue in resp.json().get("issues", []):
            fields = issue.get("fields", {})
            desc_content = ""
            if fields.get("description"):
                # ADF format — extract text from content blocks
                for block in fields["description"].get("content", []):
                    for inline in block.get("content", []):
                        desc_content += inline.get("text", "")
                    desc_content += "\n"

            # Extract comments
            comments_text = ""
            comment_data = fields.get("comment", {})
            for comment in (comment_data.get("comments") or [])[-5:]:  # last 5 comments
                author = (comment.get("author") or {}).get("displayName", "Unknown")
                body_parts = []
                if comment.get("body"):
                    for block in comment["body"].get("content", []):
                        for inline in block.get("content", []):
                            body_parts.append(inline.get("text", ""))
                comments_text += f"\n[{author}]: {''.join(body_parts)}"

            # Extract sprint info
            sprint = fields.get("sprint") or {}
            sprint_name = sprint.get("name", "")

            # Extract labels
            labels = fields.get("labels", [])
            issue_type = (fields.get("issuetype") or {}).get("name", "Issue")
            project_key = (fields.get("project") or {}).get("key", "")

            full_content = desc_content[:1500] or "No description"
            if comments_text:
                full_content += f"\n\n--- Recent Comments ---{comments_text[:500]}"
            if sprint_name:
                full_content += f"\n\nSprint: {sprint_name}"

            entities.append({
                "source_id": f"jira:issue:{issue['key']}",
                "entity_type": "task",
                "title": f"[{issue['key']}] {fields.get('summary', 'Untitled')}",
                "content": full_content,
                "source_url": f"https://{domain}/browse/{issue['key']}",
                "extra_data": {
                    "source_integration": "jira", "type": issue_type.lower(),
                    "status": (fields.get("status") or {}).get("name", ""),
                    "priority": (fields.get("priority") or {}).get("name", ""),
                    "assignee": (fields.get("assignee") or {}).get("displayName", ""),
                    "sprint": sprint_name,
                    "labels": labels,
                    "project": project_key,
                },
            })

        # Fetch active sprints from all boards
        try:
            boards_resp = await client.get(
                f"https://{domain}/rest/agile/1.0/board?maxResults=5",
                headers=headers,
            )
            if boards_resp.status_code == 200:
                for board in boards_resp.json().get("values", []):
                    try:
                        sprints_resp = await client.get(
                            f"https://{domain}/rest/agile/1.0/board/{board['id']}/sprint?state=active",
                            headers=headers,
                        )
                        if sprints_resp.status_code == 200:
                            for sprint in sprints_resp.json().get("values", []):
                                entities.append({
                                    "source_id": f"jira:sprint:{sprint['id']}",
                                    "entity_type": "document",
                                    "title": f"[Sprint] {sprint.get('name', 'Unnamed')}",
                                    "content": (
                                        f"Goal: {sprint.get('goal', 'No goal set')}\n"
                                        f"Start: {sprint.get('startDate', 'N/A')[:10]}\n"
                                        f"End: {sprint.get('endDate', 'N/A')[:10]}\n"
                                        f"State: {sprint.get('state', 'unknown')}"
                                    ),
                                    "source_url": f"https://{domain}/jira/software/projects/{board.get('location', {}).get('projectKey', '')}/boards/{board['id']}",
                                    "extra_data": {"source_integration": "jira", "type": "sprint"},
                                })
                    except Exception:
                        continue
        except Exception:
            pass

    return entities


async def _sync_linear(config: dict, since: datetime | None = None) -> list[dict]:
    token = config["token"]
    headers = {"Authorization": token, "Content-Type": "application/json"}
    entities: list[dict] = []

    query = """
    query { issues(first: 50, orderBy: updatedAt) {
        nodes { id identifier title description url state { name } priority priorityLabel
            assignee { name } team { name } createdAt updatedAt }
    }}"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.linear.app/graphql",
            headers=headers,
            json={"query": query},
        )
        resp.raise_for_status()

        for issue in resp.json().get("data", {}).get("issues", {}).get("nodes", []):
            entities.append({
                "source_id": f"linear:issue:{issue['id']}",
                "entity_type": "task",
                "title": f"[{issue.get('identifier', '')}] {issue['title']}",
                "content": (issue.get("description") or "")[:2000],
                "source_url": issue.get("url", ""),
                "extra_data": {
                    "source_integration": "linear", "type": "issue",
                    "state": (issue.get("state") or {}).get("name", ""),
                    "priority": issue.get("priorityLabel", ""),
                    "team": (issue.get("team") or {}).get("name", ""),
                },
            })

    return entities


async def _sync_confluence(config: dict, since: datetime | None = None) -> list[dict]:
    import base64
    import re
    email, token, domain = config["email"], config["token"], config["domain"]
    domain = domain.replace("https://", "").replace("http://", "").rstrip("/")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Accept": "application/json"}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch spaces first for context
        try:
            spaces_resp = await client.get(
                f"https://{domain}/wiki/api/v2/spaces?limit=25&sort=name",
                headers=headers,
            )
            if spaces_resp.status_code == 200:
                for space in spaces_resp.json().get("results", []):
                    entities.append({
                        "source_id": f"confluence:space:{space['id']}",
                        "entity_type": "document",
                        "title": f"[Confluence Space] {space.get('name', 'Unnamed')}",
                        "content": (
                            f"Key: {space.get('key', '')}\n"
                            f"Type: {space.get('type', 'global')}\n"
                            f"Description: {space.get('description', {}).get('plain', {}).get('value', 'No description')}"
                        ),
                        "source_url": f"https://{domain}/wiki/spaces/{space.get('key', '')}",
                        "extra_data": {"source_integration": "confluence", "type": "space"},
                    })
        except Exception:
            pass

        # Fetch pages with content
        resp = await client.get(
            f"https://{domain}/wiki/api/v2/pages?limit=50&sort=-modified-date&body-format=storage",
            headers=headers,
        )
        resp.raise_for_status()

        for page in resp.json().get("results", []):
            body = page.get("body", {}).get("storage", {}).get("value", "")
            # Strip HTML tags for content preview
            text = re.sub(r"<[^>]+>", " ", body)
            text = re.sub(r"\s+", " ", text).strip()

            entities.append({
                "source_id": f"confluence:page:{page['id']}",
                "entity_type": "document",
                "title": f"[Confluence] {page.get('title', 'Untitled')}",
                "content": text[:2000],
                "source_url": f"https://{domain}/wiki{page.get('_links', {}).get('webui', '')}",
                "extra_data": {
                    "source_integration": "confluence", "type": "page",
                    "space": page.get("spaceId", ""),
                    "version": page.get("version", {}).get("number", 1),
                },
            })

            # Fetch inline comments for pages with significant content
            if len(text) > 100:
                try:
                    comments_resp = await client.get(
                        f"https://{domain}/wiki/api/v2/pages/{page['id']}/footer-comments?limit=10&body-format=storage",
                        headers=headers,
                    )
                    if comments_resp.status_code == 200:
                        for comment in comments_resp.json().get("results", []):
                            cbody = comment.get("body", {}).get("storage", {}).get("value", "")
                            ctext = re.sub(r"<[^>]+>", " ", cbody)
                            ctext = re.sub(r"\s+", " ", ctext).strip()
                            if ctext:
                                entities.append({
                                    "source_id": f"confluence:comment:{comment['id']}",
                                    "entity_type": "message",
                                    "title": f"Comment on: {page.get('title', 'Untitled')}",
                                    "content": ctext[:1000],
                                    "source_url": f"https://{domain}/wiki{page.get('_links', {}).get('webui', '')}",
                                    "extra_data": {
                                        "source_integration": "confluence", "type": "comment",
                                        "page_id": page["id"],
                                    },
                                })
                except Exception:
                    continue

    return entities


async def _sync_gitlab(config: dict, since: datetime | None = None) -> list[dict]:
    token = config["token"]
    domain = config.get("domain", "gitlab.com").replace("https://", "").replace("http://", "").rstrip("/")
    headers = {"PRIVATE-TOKEN": token}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Validate + fetch projects
        resp = await client.get(
            f"https://{domain}/api/v4/projects?membership=true&per_page=30&order_by=updated_at",
            headers=headers,
        )
        resp.raise_for_status()
        projects = resp.json()

        for proj in projects:
            entities.append({
                "source_id": f"gitlab:project:{proj['id']}",
                "entity_type": "document",
                "title": proj.get("path_with_namespace", proj.get("name", "")),
                "content": (
                    f"{proj.get('description') or 'No description'}\n\n"
                    f"Stars: {proj.get('star_count', 0)} | Forks: {proj.get('forks_count', 0)}"
                ),
                "source_url": proj.get("web_url", ""),
                "extra_data": {"source_integration": "gitlab", "type": "project"},
            })

        # Issues from top 5 projects
        for proj in projects[:5]:
            try:
                ir = await client.get(
                    f"https://{domain}/api/v4/projects/{proj['id']}/issues?per_page=10&order_by=updated_at",
                    headers=headers,
                )
                ir.raise_for_status()
                for issue in ir.json():
                    entities.append({
                        "source_id": f"gitlab:issue:{proj['id']}:{issue['iid']}",
                        "entity_type": "task",
                        "title": f"[{proj['name']}] #{issue['iid']} {issue['title']}",
                        "content": (issue.get("description") or "")[:2000],
                        "source_url": issue.get("web_url", ""),
                        "extra_data": {
                            "source_integration": "gitlab", "type": "issue",
                            "state": issue.get("state", ""),
                            "labels": issue.get("labels", []),
                        },
                    })
            except Exception:
                continue

    return entities


async def _sync_google(config: dict, since: datetime | None = None) -> list[dict]:
    token = config["token"]
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try Google Drive files list
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files"
            "?pageSize=50&orderBy=modifiedTime+desc"
            "&fields=files(id,name,mimeType,webViewLink,modifiedTime,size)",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()

        for f in resp.json().get("files", []):
            mime = f.get("mimeType", "")
            etype = "document" if "document" in mime or "spreadsheet" in mime else "file"
            entities.append({
                "source_id": f"google:file:{f['id']}",
                "entity_type": etype,
                "title": f"[Google] {f.get('name', 'Untitled')}",
                "content": f"Type: {mime}\nModified: {f.get('modifiedTime', '')[:10]}",
                "source_url": f.get("webViewLink", ""),
                "extra_data": {"source_integration": "google", "type": mime},
            })

    return entities


async def _sync_microsoft365(config: dict, since: datetime | None = None) -> list[dict]:
    token = config["token"]
    headers = {"Authorization": f"Bearer {token}"}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Validate with /me
        me = await client.get("https://graph.microsoft.com/v1.0/me", headers=headers)
        me.raise_for_status()

        # Recent emails
        try:
            mail = await client.get(
                "https://graph.microsoft.com/v1.0/me/messages?$top=30&$orderby=receivedDateTime+desc"
                "&$select=id,subject,bodyPreview,webLink,receivedDateTime,from",
                headers=headers,
            )
            mail.raise_for_status()
            for msg in mail.json().get("value", []):
                sender = (msg.get("from") or {}).get("emailAddress", {}).get("name", "Unknown")
                entities.append({
                    "source_id": f"m365:mail:{msg['id']}",
                    "entity_type": "message",
                    "title": f"[Email] {msg.get('subject', 'No subject')}",
                    "content": f"From: {sender}\n{msg.get('bodyPreview', '')[:2000]}",
                    "source_url": msg.get("webLink", ""),
                    "extra_data": {"source_integration": "microsoft365", "type": "email"},
                })
        except Exception:
            pass

        # OneDrive files
        try:
            drive = await client.get(
                "https://graph.microsoft.com/v1.0/me/drive/root/children?$top=30",
                headers=headers,
            )
            drive.raise_for_status()
            for f in drive.json().get("value", []):
                entities.append({
                    "source_id": f"m365:file:{f['id']}",
                    "entity_type": "file",
                    "title": f"[OneDrive] {f.get('name', '')}",
                    "content": f"Size: {f.get('size', 0)} bytes\nModified: {f.get('lastModifiedDateTime', '')[:10]}",
                    "source_url": f.get("webUrl", ""),
                    "extra_data": {"source_integration": "microsoft365", "type": "file"},
                })
        except Exception:
            pass

    return entities


async def _sync_dropbox(config: dict, since: datetime | None = None) -> list[dict]:
    token = config["token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.dropboxapi.com/2/files/list_folder",
            headers=headers,
            json={"path": "", "limit": 50},
        )
        resp.raise_for_status()

        for entry in resp.json().get("entries", []):
            tag = entry.get(".tag", "")
            if tag == "file":
                entities.append({
                    "source_id": f"dropbox:file:{entry['id']}",
                    "entity_type": "file",
                    "title": f"[Dropbox] {entry.get('name', '')}",
                    "content": f"Path: {entry.get('path_display', '')}\nSize: {entry.get('size', 0)} bytes",
                    "source_url": f"https://www.dropbox.com/home{entry.get('path_display', '')}",
                    "extra_data": {"source_integration": "dropbox", "type": "file"},
                })
            elif tag == "folder":
                entities.append({
                    "source_id": f"dropbox:folder:{entry['id']}",
                    "entity_type": "document",
                    "title": f"[Dropbox] {entry.get('name', '')}/",
                    "content": f"Folder: {entry.get('path_display', '')}",
                    "source_url": f"https://www.dropbox.com/home{entry.get('path_display', '')}",
                    "extra_data": {"source_integration": "dropbox", "type": "folder"},
                })

    return entities


async def _sync_zoom(config: dict, since: datetime | None = None) -> list[dict]:
    token = config.get("access_token") or config.get("token", "")
    headers = {"Authorization": f"Bearer {token}"}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://api.zoom.us/v2/users/me/meetings?page_size=30&type=scheduled",
            headers=headers,
        )
        resp.raise_for_status()

        for m in resp.json().get("meetings", []):
            entities.append({
                "source_id": f"zoom:meeting:{m['id']}",
                "entity_type": "document",
                "title": f"[Zoom] {m.get('topic', 'Meeting')}",
                "content": (
                    f"Start: {m.get('start_time', 'TBD')}\n"
                    f"Duration: {m.get('duration', 0)} min\n"
                    f"Type: {'Recurring' if m.get('type') == 8 else 'Scheduled'}"
                ),
                "source_url": m.get("join_url", ""),
                "extra_data": {"source_integration": "zoom", "type": "meeting"},
            })

        # Also try recordings
        try:
            rec = await client.get(
                "https://api.zoom.us/v2/users/me/recordings?page_size=20",
                headers=headers,
            )
            rec.raise_for_status()
            for meeting in rec.json().get("meetings", []):
                for rf in meeting.get("recording_files", []):
                    if rf.get("file_type") == "MP4":
                        entities.append({
                            "source_id": f"zoom:recording:{rf['id']}",
                            "entity_type": "file",
                            "title": f"[Zoom Recording] {meeting.get('topic', 'Recording')}",
                            "content": f"Date: {meeting.get('start_time', '')[:10]}\nSize: {rf.get('file_size', 0)} bytes",
                            "source_url": rf.get("play_url", ""),
                            "extra_data": {"source_integration": "zoom", "type": "recording"},
                        })
        except Exception:
            pass

    return entities


async def _sync_figma(config: dict, since: datetime | None = None) -> list[dict]:
    token = config.get("access_token") or config.get("token", "")
    headers = {"X-Figma-Token": token}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get("https://api.figma.com/v1/me", headers=headers)
        resp.raise_for_status()

        # Get recent files from teams/projects
        me = resp.json()
        teams_resp = await client.get(
            f"https://api.figma.com/v1/me/files?page_size=30",
            headers=headers,
        )
        # /me/files may not exist — try projects
        try:
            teams_resp.raise_for_status()
            for f in teams_resp.json().get("files", []):
                entities.append({
                    "source_id": f"figma:file:{f['key']}",
                    "entity_type": "document",
                    "title": f"[Figma] {f.get('name', 'Untitled')}",
                    "content": f"Last modified: {f.get('last_modified', '')[:10]}",
                    "source_url": f"https://www.figma.com/file/{f['key']}",
                    "extra_data": {"source_integration": "figma", "type": "file"},
                })
        except Exception:
            # Fallback: just validate the token worked
            entities.append({
                "source_id": f"figma:user:{me.get('id', 'unknown')}",
                "entity_type": "person",
                "title": f"[Figma] {me.get('handle', me.get('email', 'User'))}",
                "content": f"Connected Figma account",
                "source_url": "",
                "extra_data": {"source_integration": "figma", "type": "user"},
            })

    return entities


async def _sync_asana(config: dict, since: datetime | None = None) -> list[dict]:
    token = config.get("access_token") or config.get("token", "")
    headers = {"Authorization": f"Bearer {token}"}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get user info and workspace
        me = await client.get("https://app.asana.com/api/1.0/users/me", headers=headers)
        me.raise_for_status()
        user_data = me.json().get("data", {})
        workspace_id = (user_data.get("workspaces") or [{}])[0].get("gid", "")

        if workspace_id:
            # Get recent tasks assigned to user
            tasks_resp = await client.get(
                f"https://app.asana.com/api/1.0/tasks?workspace={workspace_id}&assignee=me"
                f"&opt_fields=name,notes,completed,due_on,permalink_url,projects.name&limit=50",
                headers=headers,
            )
            tasks_resp.raise_for_status()

            for task in tasks_resp.json().get("data", []):
                project_names = ", ".join(p.get("name", "") for p in task.get("projects", []))
                entities.append({
                    "source_id": f"asana:task:{task['gid']}",
                    "entity_type": "task",
                    "title": f"[Asana] {task.get('name', 'Untitled')}",
                    "content": (task.get("notes") or "")[:2000] or f"Project: {project_names}",
                    "source_url": task.get("permalink_url", ""),
                    "extra_data": {
                        "source_integration": "asana",
                        "type": "task",
                        "completed": task.get("completed", False),
                        "due": task.get("due_on"),
                        "projects": project_names,
                    },
                })

    return entities


async def _sync_hubspot(config: dict, since: datetime | None = None) -> list[dict]:
    token = config.get("access_token") or config.get("token", "")
    headers = {"Authorization": f"Bearer {token}"}
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get recent contacts
        contacts = await client.get(
            "https://api.hubapi.com/crm/v3/objects/contacts?limit=30"
            "&properties=firstname,lastname,email,company,phone",
            headers=headers,
        )
        contacts.raise_for_status()

        for c in contacts.json().get("results", []):
            props = c.get("properties", {})
            name = f"{props.get('firstname', '')} {props.get('lastname', '')}".strip() or props.get("email", "Unknown")
            entities.append({
                "source_id": f"hubspot:contact:{c['id']}",
                "entity_type": "person",
                "title": f"[HubSpot] {name}",
                "content": (
                    f"Email: {props.get('email', 'N/A')}\n"
                    f"Company: {props.get('company', 'N/A')}\n"
                    f"Phone: {props.get('phone', 'N/A')}"
                ),
                "source_url": f"https://app.hubspot.com/contacts/{c['id']}",
                "extra_data": {"source_integration": "hubspot", "type": "contact"},
            })

        # Get recent deals
        try:
            deals = await client.get(
                "https://api.hubapi.com/crm/v3/objects/deals?limit=30"
                "&properties=dealname,amount,dealstage,closedate,pipeline",
                headers=headers,
            )
            deals.raise_for_status()
            for d in deals.json().get("results", []):
                props = d.get("properties", {})
                entities.append({
                    "source_id": f"hubspot:deal:{d['id']}",
                    "entity_type": "task",
                    "title": f"[HubSpot Deal] {props.get('dealname', 'Untitled')}",
                    "content": (
                        f"Amount: {props.get('amount', 'N/A')}\n"
                        f"Stage: {props.get('dealstage', 'N/A')}\n"
                        f"Close date: {props.get('closedate', 'N/A')}"
                    ),
                    "source_url": f"https://app.hubspot.com/deals/{d['id']}",
                    "extra_data": {"source_integration": "hubspot", "type": "deal"},
                })
        except Exception:
            pass

    return entities


async def _sync_claude(config: dict, since: datetime | None = None) -> list[dict]:
    """Claude/Anthropic — just validate the API key works."""
    token = config.get("token", "")
    entities: list[dict] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": token,
                "anthropic-version": "2023-06-01",
            },
        )
        resp.raise_for_status()
        models = resp.json().get("data", [])
        for m in models[:5]:
            entities.append({
                "source_id": f"claude:model:{m.get('id', 'unknown')}",
                "entity_type": "document",
                "title": f"[Claude Model] {m.get('display_name', m.get('id', 'unknown'))}",
                "content": f"Model: {m.get('id', '')}\nType: {m.get('type', '')}",
                "source_url": "https://console.anthropic.com",
                "extra_data": {"source_integration": "claude", "type": "model"},
            })

    return entities


# ── Syncer registry ──

_SYNCERS = {
    "github": _sync_github,
    "slack": _sync_slack,
    "google": _sync_google,
    "notion": _sync_notion,
    "jira": _sync_jira,
    "linear": _sync_linear,
    "confluence": _sync_confluence,
    "gitlab": _sync_gitlab,
    "microsoft365": _sync_microsoft365,
    "dropbox": _sync_dropbox,
    "zoom": _sync_zoom,
    "figma": _sync_figma,
    "asana": _sync_asana,
    "hubspot": _sync_hubspot,
    "claude": _sync_claude,
}
