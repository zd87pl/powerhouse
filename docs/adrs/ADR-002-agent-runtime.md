# ADR-002: Agent Runtime

## Status
Proposed

## Context
Agents need compute to execute tasks (code generation, testing, deployment). We need a runtime that scales from zero and supports both CPU and GPU workloads.

## Decision
Hybrid runtime:
- **CPU workloads** → Fly Machines (auto-suspend, pay-per-second)
- **GPU workloads** → RunPod serverless (on-demand A100/H100)
- **Orchestration** → Temporal workflows (durable, retryable)

## Consequences
- **Positive:** Cost-efficient (no idle GPU burn), durable execution (Temporal retries), fast cold start on Fly
- **Negative:** Two infrastructure providers to manage, Temporal operational complexity
- **Mitigation:** Unified control plane abstracts provider differences; Temporal managed offering if self-host is painful

## Rejected Alternatives
- Self-hosted GPU servers: idle cost prohibitive
- AWS Lambda GPU: expensive, limited GPU types
- Kubernetes: overkill for current scale
