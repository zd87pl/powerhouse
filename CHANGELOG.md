# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Phase 3: Declarative Intent Engine
- Intent Engine service: `.powerhouse.yml` reconciler that discovers intent files and reconciles declared vs. actual infrastructure state
- Schema module: full data model for intent files (project, deploy, monitoring, memory, CI configs)
- Pluggable resolver architecture: abstract Resolver base class with registry pattern
- Stub resolvers: GitHub, Vercel, Fly.io, Sentry, ChromaDB, CI Pipeline
- Reconciliation loop: diff declared vs actual state, apply changes, dry-run mode
- IntentEngine orchestrator: discovery, reconciliation, state persistence, watch loop, callbacks
- 47-test suite covering schema parsing, reconciliation, engine, resolvers, edge cases
- Example `.powerhouse.yml` in `examples/`

### Added — Initial
- Initial repository scaffold
- 10 Architecture Decision Records (ADRs 001-010)
- Docker Compose stacks for ChromaDB and n8n
- Bootstrap script for all CLIs
- Autofix daemon service
- Observability bridge (FastAPI webhooks)
- Multi-agent swarm orchestrator (prompts + state)
- Wiki schema and indexing pipeline
- 114-skill inventory
- GitHub CI workflow (lint, typecheck, secrets scan)
- MIT license

### Planned
- Project scaffold skill execution
- Phoenix tracing integration
- RunPod training pipeline
- Landing page deployment
- Stripe billing webhook
- Clerk auth integration
- Temporal workflow engine

---

## Release cadence

- **Patch** (0.0.x): Bug fixes, docs
- **Minor** (0.x.0): New features, skills
- **Major** (x.0.0): Breaking API changes

*We are pre-1.0. APIs may change without notice.*
