"""Seed script — populate the database with realistic demo data.

Usage:
    cd apps/api
    python -m scripts.seed

Idempotent: checks for existing data before inserting.
"""

import asyncio
import uuid
from datetime import datetime, UTC, timedelta

import bcrypt
from sqlalchemy import select

# Adjust path so we can import app modules
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import async_session_factory, engine
from app.db.models import (
    Organization,
    User,
    OrgMembership,
    OrgRole,
    Integration,
    IntegrationProvider,
    IntegrationStatus,
    ContextEntity,
    EntityType,
    Conversation,
    Message,
    AuditLog,
    AuditAction,
    TokenBudget,
    Task,
    TaskStatus,
    TaskPriority,
    TaskSource,
    Delegation,
    DelegationStatus,
)


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# ── Fixed UUIDs for deterministic seeding ──

ORG_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
OWNER_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
ADMIN_ID = uuid.UUID("20000000-0000-0000-0000-000000000002")
MEMBER_ID = uuid.UUID("20000000-0000-0000-0000-000000000003")

CONV_1_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
CONV_2_ID = uuid.UUID("30000000-0000-0000-0000-000000000002")

# ── Seed data definitions ──

USERS = [
    {"id": OWNER_ID, "email": "sarah@acme.dev", "name": "Sarah Chen", "password": "password123", "role": OrgRole.OWNER},
    {"id": ADMIN_ID, "email": "marcus@acme.dev", "name": "Marcus Rivera", "password": "password123", "role": OrgRole.ADMIN},
    {"id": MEMBER_ID, "email": "priya@acme.dev", "name": "Priya Sharma", "password": "password123", "role": OrgRole.MEMBER},
]

INTEGRATIONS = [
    {"provider": IntegrationProvider.SLACK, "status": IntegrationStatus.CONNECTED},
    {"provider": IntegrationProvider.GITHUB, "status": IntegrationStatus.CONNECTED},
    {"provider": IntegrationProvider.NOTION, "status": IntegrationStatus.CONNECTED},
    {"provider": IntegrationProvider.JIRA, "status": IntegrationStatus.ACTIVE},
]

CONTEXT_ENTITIES = [
    # Slack messages
    {
        "entity_type": EntityType.MESSAGE,
        "title": "Slack: Product launch timeline discussion",
        "content": (
            "Sarah Chen in #product-launch: The v2.0 launch is confirmed for March 15th. "
            "Marketing assets are ready, docs team is finalizing the migration guide. "
            "Key blockers: SSO integration testing (Marcus) and the billing API rate limit fix (Priya). "
            "Let's sync at standup tomorrow to confirm go/no-go."
        ),
        "source_url": "https://acme.slack.com/archives/C0LAUNCH/p1709000000",
        "extra_data": {"source_integration": "slack", "channel": "#product-launch"},
    },
    {
        "entity_type": EntityType.MESSAGE,
        "title": "Slack: Billing exception edge case",
        "content": (
            "Priya Sharma in #billing-edge-cases: Found the root cause of the double-charge issue. "
            "When a subscription upgrades mid-cycle and the webhook fires before the proration calculation completes, "
            "we get a race condition. Fix is in PR #142. Sarah has the most context on the billing SOP."
        ),
        "source_url": "https://acme.slack.com/archives/C0BILLING/p1709100000",
        "extra_data": {"source_integration": "slack", "channel": "#billing-edge-cases"},
    },
    {
        "entity_type": EntityType.MESSAGE,
        "title": "Slack: Q2 OKR planning thread",
        "content": (
            "Marcus Rivera in #leadership: Proposed Q2 OKRs for eng: "
            "1) Reduce P95 API latency to <200ms (currently 340ms) "
            "2) Ship SSO for enterprise tier "
            "3) Achieve 99.95% uptime (was 99.91% in Q1) "
            "4) Onboard 3 new enterprise customers. Please add comments by Friday."
        ),
        "source_url": "https://acme.slack.com/archives/C0LEAD/p1709200000",
        "extra_data": {"source_integration": "slack", "channel": "#leadership"},
    },
    # GitHub PRs
    {
        "entity_type": EntityType.DOCUMENT,
        "title": "GitHub PR #142: Fix billing proration race condition",
        "content": (
            "Author: Priya Sharma | Status: Ready for review | Branch: fix/billing-race\n\n"
            "This PR adds a distributed lock around the proration calculation to prevent "
            "the double-charge issue when subscriptions upgrade mid-cycle. "
            "Changes: billing/proration.py (+45, -12), tests/test_billing.py (+89, -0). "
            "Reviewers: Sarah Chen, Marcus Rivera. CI: All checks passing."
        ),
        "source_url": "https://github.com/acme/platform/pull/142",
        "extra_data": {"source_integration": "github", "repo": "acme/platform", "pr_number": 142},
    },
    {
        "entity_type": EntityType.DOCUMENT,
        "title": "GitHub PR #138: Add SSO SAML integration",
        "content": (
            "Author: Marcus Rivera | Status: In Progress | Branch: feature/sso-saml\n\n"
            "Implements SAML 2.0 SSO for enterprise customers. Supports Okta, Azure AD, and OneLogin. "
            "Includes IdP-initiated and SP-initiated flows. "
            "Changes: auth/saml.py (+320, -0), auth/middleware.py (+45, -8), config/sso.py (+67, -0). "
            "Blocked on: Azure AD test tenant provisioning (ETA: 2 days)."
        ),
        "source_url": "https://github.com/acme/platform/pull/138",
        "extra_data": {"source_integration": "github", "repo": "acme/platform", "pr_number": 138},
    },
    {
        "entity_type": EntityType.DOCUMENT,
        "title": "GitHub PR #145: Performance optimization for dashboard queries",
        "content": (
            "Author: Sarah Chen | Status: Merged | Branch: perf/dashboard-queries\n\n"
            "Optimized the main dashboard aggregation queries. Added composite indexes, "
            "switched to materialized views for the usage stats, and added Redis caching. "
            "P95 latency for /api/dashboard dropped from 850ms to 120ms. "
            "Changes: api/dashboard.py (+38, -95), migrations/add_indexes.py (+22, -0)."
        ),
        "source_url": "https://github.com/acme/platform/pull/145",
        "extra_data": {"source_integration": "github", "repo": "acme/platform", "pr_number": 145},
    },
    # Notion docs
    {
        "entity_type": EntityType.DOCUMENT,
        "title": "Notion: New Employee Onboarding Guide",
        "content": (
            "Welcome to Acme! This guide covers your first 30 days.\n\n"
            "Week 1: Setup & Orientation — Get accounts (Slack, GitHub, Jira, Notion), "
            "meet your team lead, attend the architecture overview session.\n\n"
            "Week 2: Codebase Deep Dive — Clone the monorepo, run the dev environment, "
            "complete the 'First PR' exercise. Buddy: assigned by your team lead.\n\n"
            "Week 3-4: First Project — Pick a starter issue labeled 'good-first-issue', "
            "pair with a senior engineer, deliver your first feature."
        ),
        "source_url": "https://notion.so/acme/onboarding-guide-abc123",
        "extra_data": {"source_integration": "notion", "database": "Engineering Wiki"},
    },
    {
        "entity_type": EntityType.DOCUMENT,
        "title": "Notion: Billing SOP — Exception Handling",
        "content": (
            "Standard Operating Procedure for billing exceptions.\n\n"
            "1. Customer reports incorrect charge → CS creates ticket in Jira\n"
            "2. Billing team reviews within 4 hours (SLA)\n"
            "3. If refund needed: auto-refund for amounts <$50, manager approval for >$50\n"
            "4. Root cause analysis required for systemic issues\n"
            "5. Updated by Sarah Chen (3 days ago) — added proration edge case documentation.\n\n"
            "Contact: Sarah Chen (billing lead), Priya Sharma (billing eng)."
        ),
        "source_url": "https://notion.so/acme/billing-sop-def456",
        "extra_data": {"source_integration": "notion", "database": "Operations"},
    },
    {
        "entity_type": EntityType.DOCUMENT,
        "title": "Notion: Architecture Decision Record — Event-Driven Billing",
        "content": (
            "ADR-023: Move billing to event-driven architecture.\n\n"
            "Decision: Migrate from synchronous billing calculations to event-driven using "
            "Kafka topics. Rationale: eliminates race conditions, improves auditability, "
            "enables real-time usage tracking. Status: Approved, implementation in Q2.\n"
            "Proposed by: Priya Sharma. Approved by: Marcus Rivera, Sarah Chen."
        ),
        "source_url": "https://notion.so/acme/adr-023-ghi789",
        "extra_data": {"source_integration": "notion", "database": "Architecture"},
    },
    # Jira tasks
    {
        "entity_type": EntityType.TASK,
        "title": "JIRA-1234: Implement SSO for enterprise tier",
        "content": (
            "Type: Epic | Priority: High | Sprint: Q2-Sprint-1 | Assignee: Marcus Rivera\n\n"
            "Implement SAML 2.0 and OIDC-based SSO for enterprise customers. "
            "Subtasks: SAML integration (in progress), OIDC integration (todo), "
            "admin UI for SSO config (todo), documentation (todo). "
            "Blocked by: Azure AD test tenant (expected this week)."
        ),
        "source_url": "https://acme.atlassian.net/browse/JIRA-1234",
        "extra_data": {"source_integration": "jira", "project": "PLATFORM"},
    },
    {
        "entity_type": EntityType.TASK,
        "title": "JIRA-1189: Fix billing proration race condition",
        "content": (
            "Type: Bug | Priority: Critical | Sprint: Q1-Sprint-6 | Assignee: Priya Sharma\n\n"
            "Customers report double-charges when upgrading mid-billing-cycle. "
            "Root cause: race between webhook handler and proration calculator. "
            "Fix: distributed lock on billing operations. PR #142 ready for review. "
            "Status: In Review. Linked: Slack #billing-edge-cases discussion."
        ),
        "source_url": "https://acme.atlassian.net/browse/JIRA-1189",
        "extra_data": {"source_integration": "jira", "project": "PLATFORM"},
    },
    {
        "entity_type": EntityType.TASK,
        "title": "JIRA-1256: Reduce API P95 latency to <200ms",
        "content": (
            "Type: Story | Priority: High | Sprint: Q2-Sprint-1 | Assignee: Sarah Chen\n\n"
            "Current P95 is 340ms, target is <200ms. Approach: "
            "1) Add composite indexes on hot queries (PR #145 - merged) "
            "2) Implement Redis caching for dashboard (done) "
            "3) Switch to connection pooling with PgBouncer (next) "
            "Progress: 65% — dashboard queries fixed, main API routes next."
        ),
        "source_url": "https://acme.atlassian.net/browse/JIRA-1256",
        "extra_data": {"source_integration": "jira", "project": "PLATFORM"},
    },
    # People
    {
        "entity_type": EntityType.PERSON,
        "title": "Sarah Chen — Engineering Lead",
        "content": (
            "Role: Engineering Lead | Team: Platform | Location: San Francisco\n"
            "Expertise: Billing systems, API performance, database optimization.\n"
            "Current focus: Q2 latency improvements, billing SOP ownership.\n"
            "Slack: @sarah.chen | GitHub: @sarahchen"
        ),
        "source_url": None,
        "extra_data": {"source_integration": "notion"},
    },
    {
        "entity_type": EntityType.PERSON,
        "title": "Marcus Rivera — Senior Engineer",
        "content": (
            "Role: Senior Engineer | Team: Platform | Location: Austin\n"
            "Expertise: Authentication, SSO/SAML, security, infrastructure.\n"
            "Current focus: Enterprise SSO implementation, Q2 OKR planning.\n"
            "Slack: @marcus.rivera | GitHub: @marcusrivera"
        ),
        "source_url": None,
        "extra_data": {"source_integration": "notion"},
    },
    {
        "entity_type": EntityType.PERSON,
        "title": "Priya Sharma — Backend Engineer",
        "content": (
            "Role: Backend Engineer | Team: Platform | Location: Remote (NYC)\n"
            "Expertise: Billing, payment systems, event-driven architecture.\n"
            "Current focus: Billing race condition fix, event-driven billing migration.\n"
            "Slack: @priya.sharma | GitHub: @priyasharma"
        ),
        "source_url": None,
        "extra_data": {"source_integration": "notion"},
    },
]

CONVERSATIONS = [
    {
        "id": CONV_1_ID,
        "user_id": OWNER_ID,
        "title": "Who has context on billing exceptions?",
        "messages": [
            {
                "role": "user",
                "content": "Who on the team has the most context on the billing exception flow?",
            },
            {
                "role": "assistant",
                "content": (
                    "Based on recent activity, **Sarah Chen** has the most context on billing exceptions:\n\n"
                    "- Updated the [Billing SOP — Exception Handling](https://notion.so/acme/billing-sop-def456) 3 days ago\n"
                    "- Active in #billing-edge-cases Slack channel\n"
                    "- Listed as billing lead in the SOP document\n\n"
                    "**Priya Sharma** is also deeply involved — she found the root cause of the double-charge "
                    "issue and has [PR #142](https://github.com/acme/platform/pull/142) ready for review.\n\n"
                    "[Source: Billing SOP](https://notion.so/acme/billing-sop-def456) · "
                    "[Source: Slack #billing-edge-cases](https://acme.slack.com/archives/C0BILLING/p1709100000)"
                ),
                "sources": [
                    {"entity_id": "seed", "title": "Billing SOP — Exception Handling", "source_url": "https://notion.so/acme/billing-sop-def456", "source_integration": "notion", "relevance_score": 0.95},
                    {"entity_id": "seed", "title": "Slack: Billing exception edge case", "source_url": "https://acme.slack.com/archives/C0BILLING/p1709100000", "source_integration": "slack", "relevance_score": 0.88},
                ],
                "model": "mock-mode",
                "tokens_used": 245,
            },
        ],
    },
    {
        "id": CONV_2_ID,
        "user_id": OWNER_ID,
        "title": "Q2 OKR status",
        "messages": [
            {
                "role": "user",
                "content": "What's the status of our Q2 engineering OKRs?",
            },
            {
                "role": "assistant",
                "content": (
                    "Here's the current status of Q2 engineering OKRs:\n\n"
                    "**1. Reduce P95 API latency to <200ms** — 65% complete\n"
                    "- Dashboard queries optimized (850ms → 120ms) via [PR #145](https://github.com/acme/platform/pull/145)\n"
                    "- Redis caching implemented. Next: PgBouncer connection pooling.\n"
                    "- Owner: Sarah Chen\n\n"
                    "**2. Ship SSO for enterprise tier** — In progress\n"
                    "- SAML integration underway in [PR #138](https://github.com/acme/platform/pull/138)\n"
                    "- Blocked on Azure AD test tenant (ETA: this week)\n"
                    "- Owner: Marcus Rivera\n\n"
                    "**3. 99.95% uptime** — Tracking (was 99.91% in Q1)\n\n"
                    "**4. Onboard 3 enterprise customers** — Not started\n\n"
                    "[Source: Q2 OKR thread](https://acme.slack.com/archives/C0LEAD/p1709200000)"
                ),
                "sources": [
                    {"entity_id": "seed", "title": "Slack: Q2 OKR planning thread", "source_url": "https://acme.slack.com/archives/C0LEAD/p1709200000", "source_integration": "slack", "relevance_score": 0.92},
                    {"entity_id": "seed", "title": "JIRA-1256: Reduce API P95 latency", "source_url": "https://acme.atlassian.net/browse/JIRA-1256", "source_integration": "jira", "relevance_score": 0.85},
                ],
                "model": "mock-mode",
                "tokens_used": 312,
            },
        ],
    },
]

TASKS = [
    {
        "title": "Fix billing proration race condition",
        "description": "Customers report double-charges when upgrading mid-billing-cycle. Root cause: race between webhook handler and proration calculator.",
        "status": TaskStatus.IN_REVIEW,
        "priority": TaskPriority.CRITICAL,
        "assignee_id": MEMBER_ID,  # Priya
        "source": TaskSource.JIRA,
        "source_url": "https://acme.atlassian.net/browse/JIRA-1189",
        "source_id": "JIRA-1189",
        "ai_summary": "PR #142 adds distributed lock. All checks passing. Sarah and Marcus assigned as reviewers.",
        "blockers": [],
        "labels": ["billing", "bugfix"],
    },
    {
        "title": "Implement SSO for enterprise tier",
        "description": "Implement SAML 2.0 and OIDC-based SSO for enterprise customers.",
        "status": TaskStatus.IN_PROGRESS,
        "priority": TaskPriority.HIGH,
        "assignee_id": ADMIN_ID,  # Marcus
        "source": TaskSource.JIRA,
        "source_url": "https://acme.atlassian.net/browse/JIRA-1234",
        "source_id": "JIRA-1234",
        "ai_summary": "SAML integration underway in PR #138. OIDC and admin UI subtasks still todo.",
        "blockers": ["Azure AD test tenant provisioning (ETA: this week)"],
        "labels": ["auth", "enterprise"],
    },
    {
        "title": "Reduce API P95 latency to <200ms",
        "description": "Current P95 is 340ms, target is <200ms. Multi-phase optimization.",
        "status": TaskStatus.IN_PROGRESS,
        "priority": TaskPriority.HIGH,
        "assignee_id": OWNER_ID,  # Sarah
        "source": TaskSource.JIRA,
        "source_url": "https://acme.atlassian.net/browse/JIRA-1256",
        "source_id": "JIRA-1256",
        "ai_summary": "65% complete. Dashboard queries fixed (850ms → 120ms). Next: PgBouncer connection pooling.",
        "blockers": [],
        "labels": ["performance"],
    },
    {
        "title": "Summarize Q2 OKR thread for leadership",
        "description": "Extract OKRs from Slack leadership thread and publish to Notion.",
        "status": TaskStatus.DONE,
        "priority": TaskPriority.MEDIUM,
        "assignee_id": None,
        "source": TaskSource.AI,
        "source_url": None,
        "source_id": "FLOW-001",
        "ai_summary": "Extracted 4 OKRs from #leadership thread. Published to Notion Q2 Planning page. 12 action items identified.",
        "blockers": [],
        "labels": ["okr", "ai-generated"],
    },
    {
        "title": "Draft onboarding checklist for new hire",
        "description": "Generate onboarding checklist from Notion guide and recent team changes.",
        "status": TaskStatus.IN_PROGRESS,
        "priority": TaskPriority.MEDIUM,
        "assignee_id": None,
        "source": TaskSource.AI,
        "source_url": None,
        "source_id": "FLOW-002",
        "ai_summary": "Generated from Onboarding Guide + recent team changes. Awaiting human review before publishing.",
        "blockers": [],
        "labels": ["onboarding", "ai-generated"],
    },
    {
        "title": "Add rate limiting to public API",
        "description": "Implement rate limiting on public API endpoints to prevent abuse.",
        "status": TaskStatus.TODO,
        "priority": TaskPriority.MEDIUM,
        "assignee_id": None,
        "source": TaskSource.JIRA,
        "source_url": "https://acme.atlassian.net/browse/JIRA-1270",
        "source_id": "JIRA-1270",
        "ai_summary": "No activity yet. Related to P95 latency work — could benefit from Redis caching already in place.",
        "blockers": [],
        "labels": ["api", "security"],
    },
]

DELEGATIONS = [
    {
        "action": 'Decline meeting: "Q2 Budget Review Sync"',
        "reason": "Conflicts with your deep work block (2-4pm). No action items for you in the agenda. Sarah Chen can represent engineering.",
        "tool": "Google Calendar",
        "confidence": 0.92,
        "proposed_for_user_id": OWNER_ID,
    },
    {
        "action": "Reply to Sarah's email re: billing exception",
        "reason": 'Draft based on your previous responses and the updated Billing SOP. Proposed reply: "Thanks Sarah — PR #142 covers the race condition fix. Priya can walk you through the distributed lock approach."',
        "tool": "Gmail",
        "confidence": 0.78,
        "proposed_for_user_id": OWNER_ID,
    },
    {
        "action": 'Update JIRA-1234 status to "In Review"',
        "reason": 'PR #138 (SSO SAML integration) was pushed for review 2 hours ago. Linked ticket still says "In Progress".',
        "tool": "Jira",
        "confidence": 0.95,
        "proposed_for_user_id": OWNER_ID,
    },
    {
        "action": "Summarize #product-launch Slack thread for standup",
        "reason": "48 messages since yesterday. Key updates: marketing assets ready, migration guide pending, two blockers identified.",
        "tool": "Slack",
        "confidence": 0.88,
        "proposed_for_user_id": OWNER_ID,
    },
    {
        "action": "Close stale PR #127 with comment",
        "reason": 'PR has been open for 23 days with no activity. Branch has merge conflicts. Proposed comment: "Closing due to inactivity — please reopen with a rebased branch if still needed."',
        "tool": "GitHub",
        "confidence": 0.85,
        "proposed_for_user_id": OWNER_ID,
    },
]

AUDIT_ENTRIES = [
    {"action": AuditAction.INTEGRATION_CONNECTED, "resource_type": "integration", "detail": {"provider": "slack"}, "tokens_consumed": 0, "cost_usd": 0.0},
    {"action": AuditAction.INTEGRATION_CONNECTED, "resource_type": "integration", "detail": {"provider": "github"}, "tokens_consumed": 0, "cost_usd": 0.0},
    {"action": AuditAction.INTEGRATION_CONNECTED, "resource_type": "integration", "detail": {"provider": "notion"}, "tokens_consumed": 0, "cost_usd": 0.0},
    {"action": AuditAction.AI_QUERY, "resource_type": "conversation", "detail": {"query": "billing exceptions"}, "tokens_consumed": 245, "cost_usd": 0.0003, "model_used": "mock-mode"},
    {"action": AuditAction.AI_RESPONSE, "resource_type": "conversation", "detail": {"sources": 2}, "tokens_consumed": 245, "cost_usd": 0.0003, "model_used": "mock-mode"},
    {"action": AuditAction.AI_QUERY, "resource_type": "conversation", "detail": {"query": "Q2 OKR status"}, "tokens_consumed": 312, "cost_usd": 0.0004, "model_used": "mock-mode"},
    {"action": AuditAction.AI_RESPONSE, "resource_type": "conversation", "detail": {"sources": 2}, "tokens_consumed": 312, "cost_usd": 0.0004, "model_used": "mock-mode"},
    {"action": AuditAction.DATA_ACCESSED, "resource_type": "context_entity", "detail": {"entity_count": 15, "action": "bulk_index"}, "tokens_consumed": 0, "cost_usd": 0.0},
]


async def seed():
    print("🌱 Seeding Recall database...")

    async with async_session_factory() as db:
        # Check if already seeded
        existing = await db.execute(select(Organization).where(Organization.id == ORG_ID))
        if existing.scalar_one_or_none():
            print("  ⏭  Seed data already exists (org found). Skipping.")
            return

        # ── Organization ──
        org = Organization(id=ORG_ID, name="Acme Corp", slug="acme-corp", token_budget_monthly=100_000)
        db.add(org)
        await db.flush()
        print("  ✓ Created org: Acme Corp")

        # ── Users + Memberships ──
        for u_data in USERS:
            user = User(
                id=u_data["id"],
                email=u_data["email"],
                name=u_data["name"],
                password_hash=_hash(u_data["password"]),
            )
            db.add(user)
        await db.flush()
        for u_data in USERS:
            membership = OrgMembership(user_id=u_data["id"], org_id=ORG_ID, role=u_data["role"])
            db.add(membership)
        await db.flush()
        print(f"  ✓ Created {len(USERS)} users with memberships")

        # ── Integrations ──
        for i_data in INTEGRATIONS:
            integration = Integration(
                org_id=ORG_ID,
                provider=i_data["provider"],
                status=i_data["status"],
                connected_by=OWNER_ID,
            )
            db.add(integration)
        await db.flush()
        print(f"  ✓ Created {len(INTEGRATIONS)} integrations")

        # ── Context Entities ──
        entity_ids = []
        for ce_data in CONTEXT_ENTITIES:
            entity = ContextEntity(
                org_id=ORG_ID,
                entity_type=ce_data["entity_type"],
                title=ce_data["title"],
                content=ce_data["content"],
                source_url=ce_data.get("source_url"),
                extra_data=ce_data.get("extra_data", {}),
                access_everyone=True,
            )
            db.add(entity)
            entity_ids.append(entity)
        await db.flush()
        print(f"  ✓ Created {len(CONTEXT_ENTITIES)} context entities")

        # ── Conversations + Messages ──
        for conv_data in CONVERSATIONS:
            conv = Conversation(
                id=conv_data["id"],
                org_id=ORG_ID,
                user_id=conv_data["user_id"],
                title=conv_data["title"],
            )
            db.add(conv)

            for msg_data in conv_data["messages"]:
                msg = Message(
                    org_id=ORG_ID,
                    conversation_id=conv_data["id"],
                    role=msg_data["role"],
                    content=msg_data["content"],
                    sources=msg_data.get("sources", []),
                    model=msg_data.get("model"),
                    tokens_used=msg_data.get("tokens_used", 0),
                )
                db.add(msg)
        await db.flush()
        print(f"  ✓ Created {len(CONVERSATIONS)} conversations with messages")

        # ── Tasks (Flow) ──
        for t_data in TASKS:
            task = Task(
                org_id=ORG_ID,
                title=t_data["title"],
                description=t_data.get("description"),
                status=t_data["status"],
                priority=t_data["priority"],
                assignee_id=t_data.get("assignee_id"),
                source=t_data["source"],
                source_url=t_data.get("source_url"),
                source_id=t_data.get("source_id"),
                ai_summary=t_data.get("ai_summary"),
                blockers=t_data.get("blockers", []),
                labels=t_data.get("labels", []),
            )
            db.add(task)
        await db.flush()
        print(f"  ✓ Created {len(TASKS)} tasks (Flow)")

        # ── Delegations (Pilot) ──
        for d_data in DELEGATIONS:
            delegation = Delegation(
                org_id=ORG_ID,
                action=d_data["action"],
                reason=d_data["reason"],
                tool=d_data["tool"],
                confidence=d_data["confidence"],
                status=DelegationStatus.PENDING,
                proposed_for_user_id=d_data["proposed_for_user_id"],
            )
            db.add(delegation)
        await db.flush()
        print(f"  ✓ Created {len(DELEGATIONS)} delegations (Pilot)")

        # ── Audit Log ──
        for i, a_data in enumerate(AUDIT_ENTRIES):
            entry = AuditLog(
                org_id=ORG_ID,
                user_id=OWNER_ID,
                action=a_data["action"],
                resource_type=a_data.get("resource_type"),
                detail=a_data.get("detail", {}),
                tokens_consumed=a_data.get("tokens_consumed", 0),
                cost_usd=a_data.get("cost_usd", 0.0),
                model_used=a_data.get("model_used"),
            )
            db.add(entry)
        print(f"  ✓ Created {len(AUDIT_ENTRIES)} audit log entries")

        # ── Token Budget ──
        period_start = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        budget = TokenBudget(
            org_id=ORG_ID,
            scope="org",
            scope_id=ORG_ID,
            monthly_limit=100_000,
            tokens_used=1114,
            period_start=period_start,
        )
        db.add(budget)
        print("  ✓ Created token budget")

        await db.commit()

    print("\n✅ Seed complete! Login with:")
    print("   Email: sarah@acme.dev")
    print("   Password: password123")


if __name__ == "__main__":
    asyncio.run(seed())
