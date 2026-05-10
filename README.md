<div align="center">

# ⚡ POWERHOUSE

### **Declare the business. Reconcile the infrastructure. Automate the fixes.**

> *"Build me a plus-size fashion store for the Polish market."*
> *Powerhouse turns that intent into projects, infrastructure checks, and agent workflows.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)

[📖 Docs](#-quick-start) · [🚀 Try It](#-quick-start) · [🤖 How Autonomy Works](#-how-it-works) · [⭐ Star](https://github.com/zd87pl/powerhouse)

</div>

---

## 🤯 What Is This?

**Powerhouse is an early-stage autonomous engineering harness.** You give it a business idea or `.powerhouse.yml` intent file. The current codebase provides:

1. **Intent parsing** from natural language into a structured app spec
2. **Project tracking** through a FastAPI control plane and Next.js dashboard
3. **Infrastructure reconciliation** with explicit synced, drifted, skipped, and error states
4. **Credential management** with encrypted-at-rest API keys
5. **Agent/runtime scaffolding** for future autofix, swarm, and business-agent loops

The product goal is larger: live scaffolding, deploys, monitoring, and self-healing PRs. Those paths are being hardened behind explicit auth, credentials, and quota gates before they are treated as production-ready.

### See it in action:

```bash
# One file. That's all you need.
cat > .powerhouse.yml << EOF
project: bez-spinki
description: "Polish plus-size fashion store"
stack: nextjs
features: [shopify-checkout, size-guide, BLIK-payments, inventory-sync]
market: PL
EOF

# Then run the API/dashboard and reconcile the declared resources.
python3 run_api.py
# → http://localhost:8080/api/health
```

---

## 🔥 The Difference

Most AI coding tools stop at **code generation**. Powerhouse is aimed at the next layer: declared resources, deploy state, observability, and repair workflows.

The current repo is a foundation for that loop. Evaluate it as a prototype control plane, not as a finished production autonomous operator.

```
YOU: "Build me a store"
     │
     ▼
┌────────────────────────────────────────────────────────────┐
│  POWERHOUSE AGENT SWARM                                     │
│                                                             │
│  🏛️ Architect    → Designs schema, plans files               │
│  👨‍💻 Coder        → Implements clean, typed, tested code      │
│  🔍 Reviewer     → Validates everything — PASS or REVISE     │
│  🚀 DevOps       → Deploys to Vercel, configures Shopify    │
│  🧪 Tester       → Fuzzes inputs, runs edge cases           │
│                                                             │
│  Target: loop until Reviewer says PASS, then open a PR.     │
└────────────────────────────────────────────────────────────┘
     │
     ▼  LIVE at https://your-store.com
     │
     ▼  3AM: Bug detected
┌────────────────────────────────────────────────────────────┐
│  🤖 AUTOFIX DAEMON                                          │
│  → Reads stack trace                                        │
│  → Diagnoses root cause                                     │
│  → Target: generate patch, open PR, verify CI               │
└────────────────────────────────────────────────────────────┘
```

> **Current status:** the control plane, dashboard, intent engine, and agent primitives exist. End-to-end autonomous repair is not production-ready yet.

---

## 🎯 What You Can Build

| Business Type | What Powerhouse Handles | Time to Live |
|---|---|---|
| 🛍️ **Ecommerce store** | Intent parsing and scaffold target; payments/inventory integrations planned | Prototype |
| 📊 **SaaS dashboard** | FastAPI + Next.js dashboard exists; auth/billing hardening planned | In progress |
| 🤖 **API service** | FastAPI control plane, project tracking, key storage, reconciliation | In progress |
| 🧪 **ML pipeline** | RunPod/training workflow is roadmap only | Planned |

---

## 🧬 How It Works

### 1. The Intent Engine
You declare **what** you want. Not how to build it.

```yaml
# .powerhouse.yml — that's the whole spec
project: my-saas
description: "Analytics dashboard for ecommerce"
stack: nextjs
auth: clerk
database: supabase
billing: stripe
monitoring: sentry+phoenix
```

The engine reads this and compares declared resources with reality:
- GitHub repo exists? If credentials are configured, verify or create it
- Deploy target present? Verify supported provider state or report skipped
- CI/CD running? Check what can be verified and report drift
- **Every resource declared = synced, drifted, skipped, or errored.** Skipped work is not reported as healthy.

### 2. The Autonomy Core
What makes Powerhouse actually autonomous — not just a fancy scaffold script:

- **Event Bus** — agents communicate through typed in-process events.
- **Episodic Memory** — in-memory fallback exists; ChromaDB/Supabase persistence is being integrated.
- **Model Router** — routing primitives exist; LiteLLM/OpenRouter hardening is still planned.
- **Deliberation Council** — a heuristic council exists; production agent deliberation is planned.

### 3. Business Agents
Domain-specific agents that run your business:

```python
# Margin monitoring — fires automatically
merch = MerchAgent()
alerts = await merch.check_margins(products)
# → "Sukienki XL: 25% margin (threshold 40%). Raise price $80→$100"

# Traffic anomaly detection
growth = GrowthAgent()
alert = await growth.detect_traffic_anomaly("/sukienki", 5000, 1000)
# → "🚨 +400% traffic spike on /sukienki. Check referrer."

# A/B test lifecycle
test = await growth.propose_ab_test(
    name="Hero CTA copy test",
    hypothesis="If we change CTA to 'Shop the Look', conversion will improve",
    variant_a="Shop Now", variant_b="Shop the Look"
)
```

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/zd87pl/powerhouse.git && cd powerhouse

# 2. Install
pip install -r requirements.txt

# 3. Run the API
python3 run_api.py
# → http://localhost:8080/api/health

# 4. Optional: run the dashboard
cd dashboard && npm install && npm run dev
# → http://localhost:3000/dashboard/setup

# 5. Create your first project
curl -X POST http://localhost:8080/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "my-store", "stack": "nextjs", "intent_yaml": "project: my-store\nstack: nextjs\ndeploy:\n  provider: vercel"}'

# 6. Trigger reconciliation
curl -X POST http://localhost:8080/api/projects/<id>/reconcile
# → Infrastructure checks are reported as synced, drifted, skipped, or error
```

`run_api.py` sets local-only development auth and dev secret encryption defaults. In production, configure Clerk, `POWERHOUSE_SECRET_KEY`, explicit `POWERHOUSE_CORS_ORIGINS`, and leave `POWERHOUSE_ALLOW_DEV_AUTH` disabled.

The setup dashboard reports each provider as connected from environment variables, configured from encrypted user-supplied keys, or missing. Required providers currently start with GitHub and Vercel so OSS users can bring their own tokens while the control plane keeps project progress visible.

---

## 🛡️ vs. Everyone Else

| | Bolt | Lovable | v0 | Replit | **Powerhouse** |
|---|---|---|---|---|---|
| Builds an app | ✅ | ✅ | ✅ | ✅ | 🏗️ |
| Deploys it | ✅ | ✅ | ✅ | ✅ | gated prototype |
| CI/CD + monitoring | ❌ | ❌ | ❌ | ❌ | 🏗️ |
| **Self-healing** | ❌ | ❌ | ❌ | ❌ | planned |
| **Remembers decisions** | ❌ | ❌ | ❌ | ❌ | prototype |
| **Agent swarms** | ❌ | ❌ | ⚠️ | ❌ | scaffolded |
| **Business agents** | ❌ | ❌ | ❌ | ❌ | prototype |
| Open source | ❌ | ❌ | ❌ | ❌ | **✅ MIT** |

> **Moat target:** closed-loop repair from production error to verified PR.

---

## 📋 Roadmap

| Phase | Status |
|---|---|
| **Foundation** — Vector memory, model routing, event bus | 🏗️ In progress |
| **Autonomy** — Agent swarms, deliberation council, autofix daemon | 🏗️ In progress |
| **SaaS** — Multi-tenant, Clerk auth, Stripe billing | 🏗️ In progress |
| **Scale** — RunPod training, enterprise SSO, SOC-2 | 📅 Q3 2026 |

---

## 🤝 Who's This For?

- **Solo founders** — prototype app and infrastructure intent quickly
- **Agencies** — manage declared resources and project status from one control plane
- **Ecommerce operators** — experiment with merchandising and growth-agent primitives
- **AI researchers** — RunPod integration for training + evaluation pipelines

---

<div align="center">

**Built with ⚡ by Ziggy**

[⭐ Star this repo](https://github.com/zd87pl/powerhouse) · [📖 Full docs](docs/) · [💬 Discussions](https://github.com/zd87pl/powerhouse/discussions)

</div>
