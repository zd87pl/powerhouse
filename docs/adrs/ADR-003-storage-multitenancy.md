# ADR-003: Storage Multi-Tenancy

## Status
Proposed

## Context
Tenant data must be isolated across object storage, vector DB, and file systems while allowing efficient cross-tenant operations for admin/analytics.

## Decision
Unified tenant namespace with prefix isolation:
```
<tenant-id>/<resource-type>/<resource-id>
```
Examples:
- `acme-corp/projects/shopify-store/v1/models/`
- `acme-corp/chroma/collections/codebase-index`
- `acme-corp/wiki/decisions/ADR-001.md`

## Consequences
- **Positive:** Single S3 bucket, simple access control via IAM policy prefixes
- **Negative:** No native multi-tenant features in ChromaDB (must proxy/enforce)
- **Mitigation:** Build ChromaDB access proxy that validates tenant before any operation

## RAG Wiki Migration
The existing filesystem-based wiki (`~/wiki/`) will migrate to the same prefix structure, backed by R2. Local cache for performance, R2 for persistence.
