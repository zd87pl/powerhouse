# Powerhouse SaaS Implementation Plan

> 14-week production-ready build. Based on ADRs 001–010 and competitive analysis.

---

## Phase 0: Security Foundation (Weeks 1–2)

### Deliverables
- [ ] Clerk organization/team auth integrated
- [ ] HashiCorp Vault deployed for tenant secrets
- [ ] Tenant schema isolation in Postgres (Supabase or Neon)
- [ ] Egress allow-lists configured on Fly Machines
- [ ] Audit log schema defined (immutable, crypto-signed)

### Key Decisions
- Clerk over Auth0: better org/team semantics, SSO-ready
- Vault over 1Password: programmatic access, self-hosted
- Schema-per-tenant over row-level security: cleaner isolation, easier backups

---

## Phase 1: Core Platform (Weeks 3–6)

### Deliverables
- [ ] Provisioning API: `POST /tenants` → creates isolated workspace in 60s
- [ ] Fly Machine manager: spawn/suspend/destroy agent containers
- [ ] Agent sandbox: restricted network, read-only base image, ephemeral workdir
- [ ] ChromaDB proxy with tenant-enforced collection scoping
- [ ] R2 bucket provisioning with tenant prefix isolation
- [ ] GitHub app integration (not PAT): per-tenant repo access
- [ ] Supabase/Neon API integration for on-demand DB creation

### API Surface
```
POST   /v1/tenants                    → create workspace
GET    /v1/tenants/{id}/status        → health + resources
POST   /v1/tenants/{id}/projects      → scaffold new project
GET    /v1/tenants/{id}/projects      → list projects
POST   /v1/tenants/{id}/agents/run    → execute agent task
GET    /v1/tenants/{id}/agents/{run}  → task status + logs
POST   /v1/tenants/{id}/knowledge/query → semantic search
```

---

## Phase 2: Product & Billing (Weeks 7–10)

### Deliverables
- [ ] Dashboard UI (Next.js + shadcn/ui)
- [ ] CLI tool (`npm install -g @powerhouse/cli`)
- [ ] Stripe integration with prepaid credits
- [ ] Usage metering: GPU hours, storage GB, API calls
- [ ] Hard quota ceilings + email alerts at 80%
- [ ] Landing page + waitlist (Vercel)

### Billing Flow
```
User tops up $100 → Stripe captures → credits added to tenant balance
                        ↓
                Usage consumed in real-time
                        ↓
                Balance hits $0 → graceful suspend (not surprise bill)
```

---

## Phase 3: Hardening (Weeks 11–12)

### Deliverables
- [ ] Penetration test (hire external or use automated tools)
- [ ] Bug bounty program announced
- [ ] SOC-2 readiness checklist
- [ ] Incident response runbook
- [ ] Rate limiting + DDoS protection (Cloudflare)
- [ ] Backup verification: restore from RTO target

---

## Phase 4: Beta (Weeks 13–14)

### Deliverables
- [ ] Invite-only beta (50 users)
- [ ] Feedback collection pipeline
- [ ] Iterate based on usage patterns
- [ ] Case studies from early adopters
- [ ] Public launch preparation

---

## Skill Inventory (114 Skills)

### Critical Path (28 skills)
- `project-scaffold` — scaffold new projects
- `flyio-setup` — Fly.io app management
- `vercel-setup` — frontend deployment
- `setup-supabase-cli` — database branching
- `eval-guardrails` — Phoenix + Promptfoo
- `autofix-daemon` — self-healing alerts
- `knowledge-base-monitor` — arXiv + blog watcher
- `agent-swarm-orchestrator` — multi-agent workflows
- `stitch-mcp` — UI generation via Stitch AI
- `subagent-driven-development` — parallel task execution
- `systematic-debugging` — error diagnosis
- `test-driven-development` — TDD workflow
- `github-pr-workflow` — PR automation
- `github-repo-management` — repo ops
- `github-issues` — issue triage
- `github-code-review` — automated review
- `global-secrets` — secrets management
- `persistent-cli-bootstrap` — CLI survival across restarts
- `hummingbot-setup` — trading infra (if relevant)
- `autoresearch-orchestrator` — RunPod training jobs
- `paperclip-setup` — headless CMS option
- `powerhouse-control-plane` — unified infra CLI
- `crawl4ai-scraper` — web scraping
- `arxiv` — paper search
- `blogwatcher` — RSS monitoring
- `polymarket` — prediction market data (research)
- `daily-ai-briefing` — automated newsletter
- `deerflow-satellite-bridge` — DeerFlow integration

### Supporting (40 skills)
- Various devops, debugging, and tool-specific skills

### Creative (25 skills)
- `stitch-mcp`, `v0-style-dashboard-design`, `popular-web-designs`, etc.

### Research (15 skills)
- `arxiv`, `blogwatcher`, `knowledge-base-monitor`, `daily-ai-briefing`

### Irrelevant to SaaS (6 skills)
- `minecraft-modpack-server`, `pokemon-player`, `ghost-track`, `hackingtool`

---

## Landing Page Strategy

### Structure (10 sections)
1. **Hero** — Dark theme, animated terminal, chat input
2. **Social proof** — "Trusted by X teams"
3. **3-step how it works** — Describe → Build → Monitor
4. **Feature grid** — Scaffold, Deploy, Monitor, Autofix, Research
5. **Comparison table** — vs Bolt, Lovable, v0, Replit, Railway
6. **Interactive demo** — Live terminal output
7. **Pricing teaser** — Four tiers + Free
8. **FAQ** — Top 10 questions
9. **CTA** — "Join the waitlist"
10. **Footer** — Links, GitHub, status page

### Tech Stack
- Next.js 14 + App Router
- shadcn/ui components
- Tailwind CSS
- Framer Motion (animations)
- Vercel deployment

### Differentiation
- Dark theme + terminal aesthetic (vs generic SaaS white)
- Live demo showing actual agent output
- Animated code blocks
- Purple/cyan accent colors
