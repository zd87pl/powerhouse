# ⚡ Powerhouse

> **10x Powerhouse — Ziggy's autonomous AI engineering organization.**  
> Self-improving infra for scaffolding, deploying, monitoring and autonomously fixing projects.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Node](https://img.shields.io/badge/Node-20+-green.svg)](https://nodejs.org)
[![Status](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

---

## 🔥 What Is This?

Powerhouse is a **self-hostable AI engineering platform** that transforms a single agent with tools into a **self-improving AI organization**. It can:

- 🏗️ **Scaffold** production-ready projects (repo + DevContainer + CI/CD + DB + deploy)
- 🤖 **Orchestrate** multi-agent swarms (Architect → Coder → Reviewer loop)
- 📡 **Monitor** production apps with real-time error detection
- 🔧 **Autofix** errors automatically (Sentry alert → diagnose → GitHub PR)
- 🧠 **Remember** everything via a persistent vector knowledge base
- 📊 **Route** tasks to the best model for the job
- 💰 **Scale** toward a multi-tenant SaaS for autonomous engineering teams

> **Competitive differentiation:** No existing product (Bolt, Lovable, v0, Replit, Railway) offers **autonomous self-healing** — error detection leading to automatic diagnosis and pull request creation. That's our moat.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        POWERHOUSE                            │
├──────────────────┬──────────────────┬───────────────────────┤
│   🧠 KNOWLEDGE    │   🤖 AGENTS      │   🚀 INFRASTRUCTURE  │
├──────────────────┼──────────────────┼───────────────────────┤
│  RAG Wiki        │  Architect      │  Fly.io (apps)        │
│  ChromaDB        │  Coder          │  RunPod (GPU)         │
│  arXiv monitor   │  Reviewer       │  Vercel (frontend)    │
│  Blog watcher    │  DevOps         │  Supabase (Postgres)  │
│                 │  Tester          │  Cloudflare R2        │
├──────────────────┼──────────────────┼───────────────────────┤
│   📡 OBSERVABILITY│   ⚙️ WORKFLOWS   │   🔐 SECURITY        │
├──────────────────┼──────────────────┼───────────────────────┤
│  Sentry          │  n8n            │  Vault secrets        │
│  Phoenix        │  Temporal       │  Clerk auth (SaaS)    │
│  Prometheus      │  Cron jobs      │  Tenant isolation     │
│  Grafana        │  Webhooks       │  Egress allow-lists   │
│  Autofix daemon  │                 │  Audit logs           │
└──────────────────┴──────────────────┴───────────────────────┘
```

---

## 📁 Repository Structure

```
powerhouse/
├── 📄 README.md                     ← You are here
├── 📄 LICENSE                       ← MIT License
├── 📄 .gitignore                    ← Secrets, data dirs, node_modules
│
├── 📂 docs/                         ← Documentation & ADRs
│   ├── architecture.md              ← System architecture deep dive
│   ├── roadmap.md                   ← 10x Powerhouse roadmap
│   ├── implementation-plan.md       ← SaaS build plan (14 weeks)
│   ├── competitive-analysis.md      ← vs Bolt, Lovable, v0, etc.
│   └── adrs/                        ← Architecture Decision Records
│       ├── ADR-001-tenant-isolation.md
│       ├── ADR-002-agent-runtime.md
│       ├── ADR-003-storage-multitenancy.md
│       ├── ADR-004-billing.md
│       ├── ADR-005-auth.md
│       ├── ADR-006-secret-management.md
│       ├── ADR-007-network-security.md
│       ├── ADR-008-observability.md
│       ├── ADR-009-disaster-recovery.md
│       └── ADR-010-vector-db-evaluation.md
│
├── 📂 infra/                        ← Infrastructure-as-code
│   ├── bootstrap/
│   │   ├── bootstrap-clis.sh        ← Install & auth all CLIs
│   │   └── .envrc.example           ← Shell env template (NO SECRETS)
│   ├── docker-compose.yml           ← ChromaDB + n8n + bridge
│   ├── chroma/
│   │   └── docker-compose.yml       ← Standalone ChromaDB
│   ├── n8n/
│   │   └── docker-compose.yml       ← Standalone n8n
│   └── scripts/
│       ├── start-services.sh        ← One-command bring-up
│       ├── stop-services.sh         ← Graceful shutdown
│       └── index-wiki.sh            ← Re-index wiki into ChromaDB
│
├── 📂 services/                     ← Custom Python services
│   ├── autofix-daemon/
│   │   ├── main.py                  ← Polls Sentry, diagnoses, opens PRs
│   │   └── requirements.txt
│   ├── observability-bridge/
│   │   ├── main.py                  ← FastAPI webhook relay
│   │   └── requirements.txt
│   └── orchestrator/
│       ├── prompts.py               ← Swarm role system prompts
│       └── state.py                 ← Persistent workflow state
│
├── 📂 skills/                       ← Hermes skill references
│   └── index.md                     ← Skill inventory + triggers
│
├── 📂 projects/                     ← Scaffoled project workspaces
│   └── .gitkeep
│
├── 📂 wiki/                         ← Persistent RAG memory
│   ├── SCHEMA.md                    ← Wiki schema definition
│   └── index.md                     ← Entry point + how to query
│
└── 📂 .github/
    └── workflows/
        └── ci.yml                   ← Lint, test, validate structure
```

---

## 🚀 Quick Start

### Prerequisites

- Linux/macOS with `bash`, `curl`, `git`, `docker`
- Persistent disk mounted at `/data/powerhouse/` (recommended)

### 1. Clone & Source

```bash
git clone https://github.com/zd87pl/powerhouse.git
cd powerhouse

# Copy example env and fill in YOUR secrets
cp infra/bootstrap/.envrc.example infra/bootstrap/.envrc
# Edit with your keys (NEVER commit this)

# Source into current shell
source infra/bootstrap/.envrc
```

### 2. Install Missing CLIs

```bash
./infra/bootstrap/bootstrap-clis.sh
```

This installs: `flyctl`, `vercel`, `supabase`, `sentry-cli`, `wrangler`, `gh` on a persistent path.

### 3. Start Core Services

```bash
./infra/scripts/start-services.sh
```

This brings up:
- 🧠 **ChromaDB** on `http://localhost:8001`
- ⚙️ **n8n** on `http://localhost:5678`
- 📡 **Observability bridge** on `http://localhost:8002`
- 🔧 **Autofix daemon** (background poller)

### 4. Verify Setup

```bash
# Check all services
docker compose -f infra/docker-compose.yml ps

# Test ChromaDB
curl http://localhost:8001/api/v1/heartbeat

# Test n8n
curl http://localhost:5678/rest/health
```

### 5. Index the Wiki

```bash
./infra/scripts/index-wiki.sh
```

This indexes all arXiv papers and wiki entries into ChromaDB for semantic search.

---

## 🔑 Required Environment Variables

Create `infra/bootstrap/.envrc` (gitignored) with these keys:

```bash
# ─── LLM / Model Routing ──────────────────────────
export OPENROUTER_API_KEY=""
export LITELLM_API_KEY=""            # If running LiteLLM proxy

# ─── Cloud Providers ──────────────────────────────
export FLY_API_TOKEN=""
export RUNPOD_API_TOKEN=""
export VERCEL_TOKEN=""
export CLOUDFLARE_API_TOKEN=""

# ─── Database ─────────────────────────────────────
export SUPABASE_ACCESS_TOKEN=""
export NEON_API_KEY=""               # Alternative to Supabase

# ─── Auth & Identity ──────────────────────────────
export GITHUB_TOKEN=""               # Repo access, PRs, issues
export CLERK_SECRET_KEY=""           # SaaS tenant auth
export CLERK_PUBLISHABLE_KEY=""

# ─── Monitoring ───────────────────────────────────
export SENTRY_AUTH_TOKEN=""          # Error ingestion + autofix
export PHOENIX_API_KEY=""            # Arize Phoenix (opt-out tracing)

# ─── Commerce ─────────────────────────────────────
export SHOPIFY_STORE_DOMAIN=""
export SHOPIFY_STOREFRONT_PUBLIC_TOKEN=""
export SHOPIFY_ADMIN_TOKEN=""

# ─── Search & Email ───────────────────────────────
export EXA_API_KEY=""
export RESEND_API_KEY=""             # Transactional email

# ─── Billing ──────────────────────────────────────
export STRIPE_SECRET_KEY=""
export STRIPE_PUBLISHABLE_KEY=""
export STRIPE_WEBHOOK_SECRET=""

# ─── Internal ─────────────────────────────────────
export POWERHOUSE_DATA_DIR="/data/powerhouse"
```

> ⚠️ **Never commit `.envrc` or any `.env` file.** They are automatically gitignored.

---

## 🛠️ What's Currently Working

| Component | Status | Details |
|-----------|--------|---------|
| Persistent disk (`/data/powerhouse`) | ✅ Live | All data survives restarts |
| Fly.io CLI | ✅ Installed | Symlinked on persistent path |
| Secrets vault | ✅ Populated | 14 keys stored securely |
| arXiv paper downloader | ✅ Working | 36 papers cached |
| Orchestrator (prompts + state) | ✅ Code written | Swarm role definitions |
| Obscura headless browser | ✅ Installed | CDP automation ready |

## 🛠️ What's Currently Broken / Not Running

| Component | Status | Details |
|-----------|--------|---------|
| ChromaDB server | ❌ Stopped | Data exists, process not running |
| n8n | ❌ Stopped | Config present, binary never started |
| Autofix daemon | ❌ Stopped | Crontab cleared |
| KB monitor | ❌ Stopped | Crontab cleared |
| Wiki indexing | ❌ Not run | 36 papers not in vector DB |
| Vercel CLI | ❌ Missing | Not installed |
| Supabase CLI | ❌ Missing | Not installed |
| Sentry CLI | ❌ Missing | Not installed |
| Wrangler | ❌ Missing | Not installed |
| GitHub CLI auth | ❌ Not auth'd | Binary missing, token stored |
| Git identity | ❌ Not set | `user.name` / `user.email` empty |
| Hermes config.yaml | ❌ Missing | No MCP server definitions |
| Crontab | ❌ Empty | No scheduled jobs |

---

## 📖 Documentation

- **[Architecture Deep Dive](docs/architecture.md)** — How all components connect
- **[Roadmap](docs/roadmap.md)** — Phase 1→4 timeline and milestones
- **[Implementation Plan](docs/implementation-plan.md)** — SaaS build plan (14 weeks)
- **[Competitive Analysis](docs/competitive-analysis.md)** — vs Bolt, Lovable, v0, Replit, Railway
- **[ADRs](docs/adrs/)** — All architecture decisions with rationale

---

## 🤝 Contributing

This is a personal AI engineering platform, but feedback and issues are welcome! Open an issue for:

- Bug reports
- Missing integrations
- Documentation improvements
- Security concerns

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

> *"The best code is the code that fixes itself."* — Powerhouse motto
