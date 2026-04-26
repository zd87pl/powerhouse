# ADR-004: Billing

## Status
Proposed

## Context
SaaS needs sustainable revenue with predictable costs for users and protection against runaway GPU spend.

## Decision
Hybrid pricing model:
- **Base subscription** ($49–$499/mo) for platform access + included resources
- **Prepaid credits** for overage (GPU hours, storage, API calls)
- **Hard quota ceilings** — services pause at $0 balance, never bill unexpectedly

## Pricing Tiers
| Tier | Monthly | GPU Hrs | Storage | Projects |
|------|---------|---------|---------|----------|
| Free | $0 | 0 | 1 GB | 1 |
| Starter | $49 | 0 (CPU) | 5 GB | 3 |
| Team | $199 | 20 hrs | 25 GB | 10 |
| Growth | $499 | 100 hrs | 100 GB | Unlimited |
| Enterprise | Custom | Unlimited | Unlimited | Unlimited |

## Consequences
- **Positive:** User cost predictability, no surprise bills, clear upgrade path
- **Negative:** Prepaid credits add friction vs pure metered
- **Mitigation:** Generous free tier for onboarding; auto-top-up option for power users

## Rejected Alternatives
- Pure metered overage: causes bill shock, churn
- Usage-only: doesn't cover platform costs
