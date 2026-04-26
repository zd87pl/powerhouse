# ADR-009: Disaster Recovery

## Status
Proposed

## Context
Platform must recover from infrastructure failures, data corruption, and regional outages with defined RPO/RTO targets.

## Decision

### Recovery Targets
| Type | RPO | RTO |
|------|-----|-----|
| Tenant data (DB, vectors, files) | 1 hour | 4 hours |
| Platform config (apps, workflows) | 0 (versioned in Git) | 1 hour |
| Secrets (Vault) | 0 (immediate replication) | 30 minutes |

### Backup Strategy
1. **PostgreSQL** — pg_dump daily to R2, point-in-time recovery via WAL archiving
2. **ChromaDB** — Snapshot + export to R2 daily
3. **S3/R2** — Cross-region replication enabled
4. **Vault** — Auto-unseal with cloud KMS, raft snapshot every 6 hours

### Runbook
- `scripts/dr-restore.sh` — Automated recovery script for common scenarios
- `docs/runbooks/` — Step-by-step guides for each failure mode

## Consequences
- **Positive:** Business continuity, customer trust
- **Negative:** Storage costs for backups, complexity
- **Mitigation:** Incremental backups, lifecycle rules (move old backups to Glacier)

## Rejected Alternatives
- No DR planning: unacceptable for SaaS
- Full multi-region active-active: too expensive for MVP
