# ADR-005: Authentication

## Status
Proposed

## Context
SaaS requires organization/team-level auth with SSO readiness for enterprise customers.

## Decision
**Clerk** for authentication and authorization:
- Organization support out of the box
- Team invitations and role-based access
- SSO-ready (SAML, OIDC on Enterprise tier)
- JWT tokens scoped per-tenant

## Token Scoping
```json
{
  "sub": "user_id",
  "org_id": "org_xxx",
  "org_role": "admin",
  "tenant_id": "acme-corp",
  "scope": "projects:read projects:write agents:run"
}
```

## Consequences
- **Positive:** Fastest path to org support, excellent DX, built-in session management
- **Negative:** Vendor dependency for auth
- **Mitigation:** Clerk data is exportable; fallback to self-hosted Keycloak if needed

## Rejected Alternatives
- Auth0: more expensive, inferior org support
- Firebase Auth: no orgs, Google dependency
- Self-hosted Keycloak: operational burden too high for MVP
