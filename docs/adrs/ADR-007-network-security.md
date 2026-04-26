# ADR-007: Network Security

## Status
Proposed

## Context
Agent containers run arbitrary code. We must prevent data exfiltration, lateral movement, and unauthorized network access.

## Decision
Defense in depth:
1. **Egress allow-lists** — agent containers can only reach whitelisted domains
2. **Network segmentation** — agents in isolated Docker networks, no host access
3. **No internet by default** — explicit opt-in per task
4. **mTLS** — all inter-service communication over mutual TLS
5. **Zero-trust** — every request authenticated, even internally

## Allow-list Example
```
github.com          ✅ (Git operations)
api.openai.com      ✅ (LLM calls, via proxy)
api.runpod.io       ✅ (GPU spawning)
api.fly.io          ✅ (App deployment)
*                   ❌ (everything else blocked)
```

## Consequences
- **Positive:** Strong security posture, prevents data exfiltration
- **Negative:** UX friction when agents need new external APIs
- **Mitigation:** Self-service allow-list requests with auto-approval for common domains; admin review for unusual requests

## Rejected Alternatives
- VPN-based isolation: adds complexity, doesn't prevent exfiltration
- Air-gapped agents: too restrictive for real work
