# Security Policy

## Supported Versions

Currently pre-1.0. All versions are best-effort.

## Reporting a Vulnerability

Email: **ziggy@powerhouse.dev**

Please include:
- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

We aim to respond within 48 hours and ship a fix within 7 days for critical issues.

## Security Checklist

Before contributing, ensure:
- [ ] No secrets in code (use `infra/bootstrap/.envrc`)
- [ ] No hardcoded credentials
- [ ] SQL queries parameterized
- [ ] User input sanitized
- [ ] Dependencies up to date (`pip list --outdated`)

## Known Limitations

- ChromaDB currently runs without auth (localhost only)
- n8n basic auth uses default password if not changed
- Agent containers have egress allowlists but are not yet fully sandboxed

These are tracked in the roadmap and will be hardened before v1.0.
