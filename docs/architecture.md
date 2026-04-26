# Powerhouse Architecture

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                                │
│   Slack / Discord / CLI / Dashboard / API                            │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────┐
│                       HERMES AGENT CORE                              │
│   Tool Router → Model Selector → Action Executor                     │
│   (OpenRouter / LiteLLM proxy for model routing)                     │
└──────────┬───────────────┬───────────────┬──────────┬───────────────┘
           │               │               │          │
┌──────────▼────┐ ┌────────▼─────┐ ┌───────▼──────┐ ┌▼──────────────┐
│ 🧠 KNOWLEDGE  │ │ 🤖 SWARMS    │ │ 🚀 DEPLOY    │ │ 📡 OBSERVE    │
├───────────────┤ ├──────────────┤ ├──────────────┤ ├───────────────┤
│ RAG Wiki      │ │ Architect    │ │ Fly.io       │ │ Sentry        │
│ ChromaDB      │ │ Coder        │ │ Vercel       │ │ Phoenix       │
│ Raw papers    │ │ Reviewer     │ │ RunPod       │ │ Prometheus    │
│ Blog feeds    │ │ DevOps       │ │ Supabase     │ │ Grafana       │
│ Decision log  │ │ Tester       │ │ Cloudflare   │ │ Autofix loop  │
└───────┬───────┘ └──────┬───────┘ └──────┬───────┘ └───────┬───────┘
        │                │                │                 │
        └────────────────┴──────┬─────────┴─────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   PERSISTENT DISK      │
                    │   /data/powerhouse/    │
                    │                        │
                    │ • hermes/secrets/.env  │
                    │ • chroma-data/         │
                    │ • n8n-data/            │
                    │ • wiki/                │
                    │ • projects/            │
                    │ • orchestrator/runs/   │
                    └────────────────────────┘
```

## Component Details

### Knowledge Layer (RAG)
- **Wiki**: Structured markdown memory at `wiki/` following SCHEMA.md
- **ChromaDB**: Vector DB for semantic search across code, papers, decisions
- **arXiv monitor**: Weekly cron downloads new ML papers, indexes into ChromaDB
- **Blog watcher**: RSS/Atom feed monitor for industry news

### Agent Swarms
- **Architect**: Analyzes requests, produces technical specs
- **Coder**: Implements code from Architect specs
- **Reviewer**: Validates code against specs; PASS or REVISE
- **DevOps**: Deploy, configure infrastructure, manage secrets
- **Tester**: Run tests, verify functionality

### Deployment Targets
| Platform | Use Case | Status |
|----------|----------|--------|
| Fly.io | Backend services, CPU agents | ✅ CLI installed |
| Vercel | Next.js frontends, landing pages | ❌ Not installed |
| RunPod | GPU training, autoresearch | ✅ Token stored |
| Cloudflare | Edge workers, R2 storage | ✅ Token stored |
| Supabase | Postgres DB, auth, storage | ✅ Token stored |

### Observability Stack
- **Sentry**: Error tracking + source for autofix loop
- **Phoenix (Arize)**: LLM tracing, prompt observability
- **Prometheus + Grafana**: Metrics dashboards
- **Autofix daemon**: Polls Sentry → diagnoses with LLM → opens GitHub PR

## Data Flow

### 1. New Project Request
```
User request → Hermes → Architect spec → Coder implementation
                                     ↓
                              Reviewer validation
                              ↓ (PASS)
                              GitHub PR → CI/CD → Deploy
```

### 2. Production Error
```
App error → Sentry → Webhook → Observability bridge
                                    ↓
                              Autofix daemon polls
                                    ↓
                              LLM diagnosis
                                    ↓
                              GitHub PR with patch
```

### 3. Knowledge Ingestion
```
arXiv RSS → Weekly cron → PDF download → Markdown extraction
                                              ↓
                                        ChromaDB indexing
                                              ↓
                                        Wiki update
```

## Multi-Tenancy Model (SaaS Phase)

```
Tenant A ─┐
Tenant B ─┼─→ Clerk auth ─→ Tenant isolation middleware
Tenant C ─┘         ↓
            ┌───────▼────────┐
            │  API Gateway   │
            └───────┬────────┘
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
Schema-A         Schema-B         Schema-C  (Supabase/Neon)
Coll-A           Coll-B           Coll-C    (ChromaDB)
Bucket-A         Bucket-B         Bucket-C  (R2)
```

All decisions documented in [ADRs](adrs/).
