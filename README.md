# Recall

**AI-native Work OS** — one platform that understands everything happening across your org.

Three products, one unified context graph:

- 🧠 **Ask** — Enterprise AI assistant with RAG-powered chat
- 🤖 **Pilot** — Personal delegation agent that proposes actions for you to approve
- 📋 **Flow** — AI-native task management with automatic status updates

---

## ✨ Features

### Ask
- 💬 Real-time SSE streaming chat
- 🔍 Hybrid search across all connected tools (Weaviate + SQL fallback)
- 📎 Source attribution with clickable references
- 🗂️ Conversation history with auto-titling

### Pilot
- 📥 AI-proposed actions across your tools (Calendar, Email, Jira, Slack, GitHub)
- ✅ One-click approve / reject / undo
- 📊 Confidence scores and approval rate tracking
- 📝 Full audit trail for every decision

### Flow
- 📌 Tasks synced from Jira, GitHub, Linear, or created manually
- 🤖 AI-generated summaries and blocker detection
- 🏷️ Priority, status, labels, assignee management
- ➡️ Quick status transitions (To Do → In Progress → In Review → Done)

### Governance
- 📈 Token usage and cost tracking dashboard
- 📒 Complete audit log of all AI actions
- 🔒 Role-based access control (Owner / Admin / Member / Guest)
- 💰 Monthly token budget enforcement

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────┐
│  Frontend — Next.js 15 / React 19 / Tailwind │
│  13 pages, SSE streaming, JWT auth           │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  API — FastAPI (async) / 42 routes           │
│  Auth, Ask, Flow, Pilot, Skills, Governance  │
└──────┬───────┬───────┬───────┬───────────────┘
       │       │       │       │
   ┌───▼──┐ ┌─▼──┐ ┌──▼──┐ ┌─▼────┐
   │Postgr│ │Weav│ │LiteL│ │Compos│
   │  es  │ │iate│ │ LM  │ │  io  │
   └──────┘ └────┘ └─────┘ └──────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| 🖥️ Frontend | Next.js 15, React 19, Tailwind CSS 4, Framer Motion, Lucide |
| ⚙️ Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| 🗄️ Database | PostgreSQL 16, Alembic migrations |
| 🔎 Search | Weaviate (vector + BM25 hybrid), SQL ILIKE fallback |
| 🤖 LLM | LiteLLM proxy (OpenAI, Anthropic, any provider) |
| 🔐 Auth | JWT (HS256), bcrypt password hashing |
| 🔗 Integrations | Composio (Slack, GitHub, Jira, Notion, Google, etc.) |
| 📦 Monorepo | Turborepo + pnpm workspaces |
| 🐳 Infra | Docker Compose — core: Postgres, Redis, Weaviate, LiteLLM, API, Web. **Optional profile `extras`:** Temporal (+ UI), MinIO (S3) for future workflows / attachments |

---

## 🎯 Product positioning

Recall is a **team / org “Work OS”** (connected SaaS + governed AI + human-approved actions). The ideal customer is a **small or mid-size team** that lives in Slack, GitHub, Jira, and similar tools—not a solo user looking for a markdown vault.

**Compared to Obsidian or Joplin:** those products are **personal knowledge bases** (local notes, markdown, plugins, offline). Recall does not compete on the same axis today. If you need Obsidian-like **local-first PKM**, that would be a **separate product wedge** (markdown import/export, E2E encryption, offline read) and is **out of scope** for the current codebase unless explicitly prioritized.

---

## 🚀 Quick Start

### Prerequisites

- 🐳 Docker & Docker Compose
- 📦 Node.js 20+ & pnpm
- 🐍 Python 3.12+

### 1. Clone & install

```bash
git clone https://github.com/Phani3108/Recall.git
cd Recall
pnpm install
```

### 2. Start infrastructure

```bash
docker compose up -d
```

This starts the **default** stack: Postgres (`:5434`), Redis (`:6380`), Weaviate (`:8080`), LiteLLM (`:4000`), API (`:8000`), Web (`:3000`).

**Optional** Temporal, Temporal UI, and MinIO (not required by the API today):

```bash
docker compose --profile extras up -d
```

The API uses **Redis-backed HTTP rate limiting** when `REDIS_RATE_LIMITING=true` and `APP_ENV` is not `test`; otherwise it uses an in-process limiter (fine for local dev).

### 3. Set up the API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. Run migrations & seed

```bash
alembic upgrade head
python -m scripts.seed
```

This creates demo data: 3 users, 15 context entities, 6 tasks, 5 delegations.

### 5. Start servers

```bash
# Terminal 1 — API
cd apps/api
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd apps/web
pnpm dev
```

### 6. Open the app

- 🌐 Frontend: [http://localhost:3000](http://localhost:3000)
- ⚡ API: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- 📚 API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Demo login

| Email | Password | Role |
|---|---|---|
| `sarah@acme.dev` | `password123` | Owner |
| `marcus@acme.dev` | `password123` | Admin |
| `priya@acme.dev` | `password123` | Member |

---

## 📁 Project Structure

```
Recall/
├── apps/
│   ├── api/                  # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/routes/   # 11 route modules (42 endpoints)
│   │   │   ├── db/           # Models, migrations, session
│   │   │   └── services/     # Context engine, LLM service, Integration hub
│   │   ├── scripts/seed.py   # Demo data seeder
│   │   └── alembic/          # DB migrations
│   └── web/                  # Next.js frontend
│       └── src/
│           ├── app/          # 13 pages (App Router)
│           ├── components/   # Landing page sections
│           └── lib/          # API client, auth context
├── docker-compose.yml        # Infrastructure services
├── turbo.json                # Monorepo config
└── pnpm-workspace.yaml
```

---

## 🔌 API Endpoints (42 routes)

| Group | Routes | Description |
|---|---|---|
| 🏥 Health | `GET /health` | Service status |
| 🔐 Auth | `POST /auth/login`, `/register`, `GET /auth/me` | JWT authentication |
| 🏢 Orgs | `GET /orgs/current`, `/members` | Organization management |
| 👤 Users | `GET /users/me`, `PATCH /users/me` | Profile management |
| 🔗 Integrations | CRUD + `/connect`, `/disconnect`, `/status` | OAuth tool connections |
| 🔎 Context | `POST /context/search` | Hybrid search |
| 💬 Ask | Conversations CRUD + `/messages`, `/messages/stream` | RAG chat + SSE streaming |
| 📋 Flow | `GET/POST/PATCH/DELETE /flow/tasks`, `/stats/summary` | Task management |
| 🤖 Pilot | `GET/POST /pilot/delegations`, `/delegations/suggest`, `/approve`, `/reject`, `/undo`, `/execute`, `/stats` | Delegation inbox + structured execution payload |
| ⚡ Skills | CRUD + `/vote` | Reusable AI workflows |
| 📊 Governance | `GET /governance/dashboard`, `/audit-logs` | Usage tracking |

---

## ⚙️ Configuration

Copy `.env.example` and configure:

```bash
cp .env.example .env
```

Key settings:

| Variable | Purpose | Required |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection | ✅ |
| `APP_SECRET_KEY` | JWT signing key | ✅ |
| `OPENAI_API_KEY` | LLM provider key | ❌ (mock mode works without it) |
| `COMPOSIO_API_KEY` | Integration OAuth flows | ❌ |
| `WEAVIATE_URL` | Vector search | ❌ (SQL fallback available) |

> 💡 **Mock mode**: When no LLM API key is set, Ask returns contextual mock responses using your seed data — perfect for development.

---

## 📜 License

MIT
