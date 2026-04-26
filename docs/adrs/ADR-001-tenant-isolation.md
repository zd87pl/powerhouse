# ADR-001: Tenant Isolation

## Status
Proposed

## Context
Powerhouse SaaS must host multiple tenants (users/teams) on shared infrastructure while guaranteeing data isolation and security.

## Decision
Implement **schema-per-tenant** isolation across all storage layers:

| Layer | Isolation Mechanism |
|-------|---------------------|
| PostgreSQL | Schema-per-tenant (`tenant_a.users`, `tenant_a.projects`) |
| ChromaDB | Collection-per-tenant with prefixed names |
| S3/R2 | Prefix-per-tenant (`tenant-a/projects/`, `tenant-a/models/`) |
| Fly Machines | Label-based scheduling, separate networks |

## Consequences
- **Positive:** Strong isolation, easy per-tenant backup/restore, clean audit boundaries
- **Negative:** Schema migration complexity (must run per-schema), slightly more DB connections
- **Mitigation:** Use migration tooling that iterates schemas; connection pooling

## Rejected Alternatives
- Row-level security (RLS): harder to audit, performance overhead on large tables
- Database-per-tenant: too expensive at scale, connection limits
