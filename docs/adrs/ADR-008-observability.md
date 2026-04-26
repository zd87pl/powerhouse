# ADR-008: Observability

## Status
Proposed

## Context
We need visibility into system health, agent performance, LLM usage, and errors across all components.

## Decision
Multi-layer observability:

| Layer | Tool | Purpose |
|-------|------|---------|
| Errors | Sentry | Application error tracking, source for autofix |
| LLM Tracing | Phoenix (Arize) | Prompt/response logging, cost tracking |
| Metrics | Prometheus + Grafana | Infrastructure metrics, dashboards |
| Logs | Loki + Grafana | Centralized log aggregation |
| Uptime | Better Stack | External health checks, status page |
| Autofix | Custom daemon | Polls Sentry → diagnoses → opens PRs |

## Phoenix Configuration
- Opt-out by default (user preference): tracing disabled unless explicitly enabled
- When enabled: captures all LLM calls with full prompts, responses, latency, cost
- Data retained 30 days, then archived to R2

## Consequences
- **Positive:** Full visibility, cost control, automated error response
- **Negative:** Phoenix data volume can be large
- **Mitigation:** Sampling (1% by default), compression, S3 lifecycle rules

## Rejected Alternatives
- Datadog: too expensive at scale
- Self-hosted ELK: operational burden too high
