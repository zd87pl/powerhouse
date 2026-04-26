# ADR-006: Secret Management

## Status
Proposed

## Context
Tenants will store sensitive credentials (API keys, DB passwords, tokens) that must never leak between tenants or be readable by platform operators.

## Decision
**HashiCorp Vault** with KV v2 secrets engine:
- Each tenant gets a dedicated Vault path: `secret/powerhouse/tenants/{tenant-id}/`
- Dynamic database credentials (PostgreSQL, etc.) with automatic rotation
- Transit encryption for sensitive data at rest
- Audit logging of all secret access

## Architecture
```
App requests secret → Vault validates JWT → returns credential
                         ↓
              Audit log: who, what, when
```

## Consequences
- **Positive:** Industry-standard, dynamic credentials, automatic rotation
- **Negative:** Vault operational complexity, HA setup needed
- **Mitigation:** Start with single-node Vault; migrate to HA cluster before enterprise tier

## Rejected Alternatives
- 1Password Secrets Automation: great UX but not self-hosted
- AWS Secrets Manager: lock-in, no cross-cloud portability
- Environment variables: insecure, no rotation, no audit
