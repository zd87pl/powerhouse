<div align="center">

# ⚡ POWERHOUSE

### **You describe the business. AI builds everything else.**

> *"Build me a plus-size fashion store for the Polish market."*
> *5 minutes later → live store, real payments, inventory management, automated marketing.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)

[📖 Docs](#-quick-start) · [🚀 Try It](#-quick-start) · [🤖 How Autonomy Works](#-how-it-works) · [⭐ Star](https://github.com/zd87pl/powerhouse)

</div>

---

## 🤯 What Is This?

**Powerhouse is an AI engineering team in a box.** You give it a business idea. It:

1. **Scaffolds** the entire project — repo, CI/CD, database, monitoring
2. **Builds** the thing — frontend, backend, payments, auth, everything
3. **Deploys** it to production — live URL, real infrastructure
4. **Monitors** it — catches errors before users do
5. **Heals** it — detects bugs at 3am, writes the fix, opens a PR, merges it

No "here's some starter code, good luck." **Done means live and self-healing.**

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

# Then...
powerhouse build
# → 5 minutes later: https://bez-spinki.pl is live
# → Products synced, payments working, monitoring active
# → Errors? The autofix daemon handles them while you sleep
```

---

## 🔥 The Difference

Every AI coding tool stops at **code generation**. You still have to wire up databases, configure auth, set up monitoring, handle errors at 3am.

Powerhouse doesn't stop until your business is **running, watched, and self-repairing.**

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
│  They loop until Reviewer says PASS. Then opens a PR.       │
└────────────────────────────────────────────────────────────┘
     │
     ▼  LIVE at https://your-store.com
     │
     ▼  3AM: Bug detected
┌────────────────────────────────────────────────────────────┐
│  🤖 AUTOFIX DAEMON                                          │
│  → Reads stack trace                                        │
│  → Diagnoses root cause                                     │
│  → Generates patch → commits → opens PR                     │
│  → CI passes → MERGED                                       │
│  → You wake up to: "Fixed while you were sleeping ✨"       │
└────────────────────────────────────────────────────────────┘
```

> **This isn't ChatGPT with a deploy button.** This is an autonomous engineering organization that doesn't sleep.

---

## 🎯 What You Can Build

| Business Type | What Powerhouse Handles | Time to Live |
|---|---|---|
| 🛍️ **Ecommerce store** | Shopify backend, Next.js storefront, BLIK/Stripe payments, inventory sync, size guides, shipping rates | **5 min** |
| 📊 **SaaS dashboard** | Clerk auth, Supabase, Stripe billing, real-time analytics, team management | **3 min** |
| 🤖 **API service** | FastAPI, rate limiting, API keys, webhooks, OpenAPI docs, monitoring | **2 min** |
| 🧪 **ML pipeline** | RunPod training, model evaluation, experiment tracking, dataset versioning | **10 min** |

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

The engine reads this, reconciles it against reality, and makes it true:
- GitHub repo exists? If not → creates it
- Database provisioned? If not → provisions it  
- CI/CD running? If not → configures it
- **Every resource declared = verified or created.** No drift. No forgotten configs.

### 2. The Autonomy Core
What makes Powerhouse actually autonomous — not just a fancy scaffold script:

- **Event Bus** — agents communicate through typed events. Deploy completes → inventory agent notices → syncs products. No polling, no cron.
- **Episodic Memory** — every decision, error, and fix is remembered. "Have we seen this bug before?" → Yes, here's what worked.
- **Model Router** — complex architecture goes to Claude Opus. Quick fixes go to Llama (free). Saves 70% on API costs.
- **Deliberation Council** — 5 agents vote on high-stakes actions. Hotfix deploy? 4/5 approve → proceed. Rollback? Rejected.

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

# 4. Create your first project
curl -X POST http://localhost:8080/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "my-store", "stack": "nextjs", "intent_yaml": "project: my-store\nstack: nextjs\ndeploy:\n  provider: vercel"}'

# 5. Trigger reconciliation
curl -X POST http://localhost:8080/api/projects/<id>/reconcile
# → Infrastructure reconciles to match your intent
```

---

## 🛡️ vs. Everyone Else

| | Bolt | Lovable | v0 | Replit | **Powerhouse** |
|---|---|---|---|---|---|
| Builds an app | ✅ | ✅ | ✅ | ✅ | ✅ |
| Deploys it | ✅ | ✅ | ✅ | ✅ | ✅ |
| CI/CD + monitoring | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Self-healing** | ❌ | ❌ | ❌ | ❌ | **✅** |
| **Remembers decisions** | ❌ | ❌ | ❌ | ❌ | **✅** |
| **Agent swarms** | ❌ | ❌ | ⚠️ | ❌ | **✅** |
| **Business agents** | ❌ | ❌ | ❌ | ❌ | **✅** |
| Open source | ❌ | ❌ | ❌ | ❌ | **✅ MIT** |

> **Our moat:** When your store crashes at 3am, Bolt gives you an error message. Powerhouse fixes it while you sleep.

---

## 📋 Roadmap

| Phase | Status |
|---|---|
| **Foundation** — Vector memory, model routing, event bus | ✅ |
| **Autonomy** — Agent swarms, deliberation council, autofix daemon | ✅ |
| **SaaS** — Multi-tenant, Clerk auth, Stripe billing | 🏗️ In progress |
| **Scale** — RunPod training, enterprise SSO, SOC-2 | 📅 Q3 2026 |

---

## 🤝 Who's This For?

- **Solo founders** — Ship a complete business in an afternoon, not a quarter
- **Agencies** — One platform for all client projects. Auto-deploy, auto-fix, auto-bill
- **Ecommerce operators** — Merchandising agent watches margins, growth agent runs A/B tests
- **AI researchers** — RunPod integration for training + evaluation pipelines

---

<div align="center">

**Built with ⚡ by Ziggy**

[⭐ Star this repo](https://github.com/zd87pl/powerhouse) · [📖 Full docs](docs/) · [💬 Discussions](https://github.com/zd87pl/powerhouse/discussions)

</div>
