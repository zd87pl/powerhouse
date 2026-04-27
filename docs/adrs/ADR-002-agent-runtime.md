# ADR-002: Agent Runtime

## Status
Proposed

## Context
Agents need compute to execute tasks (code generation, testing, deployment). We need a runtime that scales from zero and supports both CPU and GPU workloads.

## Decision
Hybrid runtime:
- **CPU workloads (sporadic)** → Fly Machines (auto-suspend, pay-per-second)
- **CPU workloads (always-on, managed DB)** → Railway (managed Postgres + Redis, PR previews)
- **GPU workloads** → RunPod serverless (on-demand A100/H100)
- **Orchestration** → Temporal workflows (durable, retryable)

## Deployment Matrix

| Stack | Default Target | Override Flag | Rationale |
|-------|---------------|---------------|-----------|
| Next.js frontend | Vercel | `--deploy flyio` | CDN, edge, serverless |
| Next.js full-stack | Railway | `--deploy flyio` | Always-on backend + managed DB |
| FastAPI backend | Fly.io | `--deploy railway` | Auto-suspend, cheapest sporadic |
| FastAPI + Postgres | Railway | `--deploy flyio` | Managed DB, PR previews |
| ML training | RunPod | N/A | GPU required |

## Consequences
- **Positive:** Cost-efficient (no idle GPU burn), durable execution (Temporal retries), fast cold start on Fly, zero-ops DB on Railway
- **Negative:** Three infrastructure providers to manage, Temporal operational complexity
- **Mitigation:** Unified control plane (`powerhouse-control-plane` skill) abstracts provider differences; Temporal managed offering if self-host is painful

## Rejected Alternatives
- Self-hosted GPU servers: idle cost prohibitive
- AWS Lambda GPU: expensive, limited GPU types
- Kubernetes: overkill for current scale
