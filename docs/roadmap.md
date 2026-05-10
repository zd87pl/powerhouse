# 10x Powerhouse Roadmap

## Mission
Transform from "agent with tools" into a self-improving AI engineering organization that can scaffold, build, deploy, monitor, and autonomously improve projects.

---

## Phase 1 — Foundation ✅ In Progress

1. **Vector DB per project** (ChromaDB)
   - ✅ Auto-download arXiv papers (36 cached)
   - ❌ Not yet indexed into ChromaDB
   - ❌ No semantic search API

2. **DevContainer definitions** for all active repos
   - ❌ No project scaffoled yet
   - ❌ No `.devcontainer/devcontainer.json`

3. **LiteLLM model router**
   - ❌ Not configured
   - ❌ Direct OpenRouter calls only

---

## Phase 2 — Autonomy

4. **Multi-agent swarm orchestrator**
   - ✅ Prompts + state classes written
   - ❌ Never executed end-to-end
   - ❌ No integration with Hermes delegation

5. **Observability webhook bridge**
   - ✅ FastAPI scaffold exists
   - ❌ Not running
   - ❌ No real alert processing

6. **Database branching for PR previews**
   - ❌ No Supabase project created
   - ❌ No Neon project

---

## Phase 3 — Scale

7. **n8n / Temporal durable workflows**
   - ✅ n8n data dir present
   - ❌ n8n server never started
   - ❌ No workflows defined

8. **Fine-tuned coding assistant** — SKIPPED per user request

9. **Self-healing knowledge base**
   - ✅ 36 arXiv papers downloaded
   - ❌ Not indexed
   - ❌ KB monitor cron paused

---

## Phase 4 — SaaS: Powerhouse Agentic Harness

**Vision:** Package our internal stack as a multi-tenant SaaS.  
**Tagline:** *"Heroku for Autonomous AI Engineering Teams.*"

### Product Promise
- One signup → isolated tenant workspace live in 60 seconds
- Pre-loaded skills (scaffold, deploy, debug, research)
- Pre-wired infrastructure (Fly, RunPod, Vercel, GitHub)
- Autofix: error → agent diagnoses → PR opened
- Knowledge persistence: tenant wiki, vector memory, decision logs

### Architecture Decisions
All stored in `docs/adrs/`:
- ADR-001: Tenant Isolation (schema-per-tenant)
- ADR-002: Agent Runtime (Fly Machines + RunPod serverless)
- ADR-003: Storage Multi-Tenancy (prefix-per-tenant S3)
- ADR-004: Billing (hybrid tier + prepaid credits)
- ADR-005: Auth (Clerk for org/team + SSO)
- ADR-006: Secret Management (Vault)
- ADR-007: Network Security (egress allow-lists)
- ADR-008: Observability (Phoenix + Sentry + Prometheus)
- ADR-009: Disaster Recovery (backups, RPO/RTO)
- ADR-010: Vector DB Evaluation (ChromaDB vs Qdrant)

### Pricing Tiers
| Tier | Monthly | GPU Hours | Storage | Target |
|------|---------|-----------|---------|--------|
| Free | $0 | 0 (CPU) | 1 GB | Viral growth, demos |
| Starter | $49 | 0 (CPU) | 5 GB | Individual developers |
| Team | $199 | 20 hrs | 25 GB | Small agencies |
| Growth | $499 | 100 hrs | 100 GB | Active teams |
| Enterprise | Custom | Unlimited | Unlimited | Internal platform teams |

### Timeline: 14 Weeks
| Phase | Duration | Focus |
|-------|----------|-------|
| Phase 0: Security Foundation | 2 wks | Clerk auth, Vault secrets, tenant schemas |
| Phase 1: Core Platform | 4 wks | Provisioning API, Fly Machine manager, agent sandbox |
| Phase 2: Product & Billing | 4 wks | Scaffold API, dashboard, CLI, Stripe + prepaid credits |
| Phase 3: Hardening | 2 wks | Audit logs, pentest, SOC-2 readiness |
| Phase 4: Beta | 2 wks | Invite-only beta, feedback, iteration |

### Critical Preconditions (Must Have Before Tenant Zero)
1. ❌ Egress allow-lists for agent containers
2. ❌ Per-tenant DB credentials (not shared superuser)
3. 🏗️ Secrets management (local Fernet encryption now, Vault/1Password still planned)
4. ❌ Crypto-signed audit logs
5. ❌ Daily GPU spend caps with kill switch
6. ❌ ChromaDB access proxy with tenant enforcement
7. ❌ Free tier for competitive parity
8. ❌ Prepaid credits model (not pure metered overage)
9. ❌ Demo-first onboarding (show value before OAuth hell)
10. ❌ Pentest / bug bounty before public launch

---

## Competitive Landscape
| Competitor | Entry Price | Free Tier | Has Autonomy | Has Monitoring |
|------------|-------------|-----------|--------------|----------------|
| Bolt.new | $25 | ✅ 1M tokens | ❌ Chat only | ❌ |
| Lovable | $25 | ✅ | ❌ Chat only | ❌ |
| v0 | $30/user | ✅ | ⚠️ Plans tasks | ❌ |
| Replit | $7 | ✅ | ❌ AI assist | ❌ |
| Railway | $5 | ✅ Trial | ❌ No AI | ✅ Infra only |
| **Powerhouse** | **$49** | **✅ Planned** | **✅ Self-healing** | **✅ Built-in** |

> **Key insight:** No competitor offers autonomous self-healing (error → diagnosis → PR). This is our primary differentiation.
