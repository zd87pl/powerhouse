# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Autofix: error diagnosis
- Heuristic error-diagnosis engine (`services/instill_api/diagnosis.py`): classifies a
  stack trace into category, severity, root cause, concrete fix steps, and the files most
  likely involved. Deterministic and dependency-free — runs with no API keys.
- Recognises ~25 common Python and JS/TS/Next.js failure modes (missing dependency,
  null/None reference, missing key, connection refused, DB constraint, hydration mismatch,
  render loop, 5xx, rate limit, and more), with a generic triage fallback for the rest.
- `POST /api/demo/diagnose` (public) and `POST /api/diagnose` (authenticated) endpoints,
  LLM-enriched via OpenRouter when a key is present, heuristic otherwise.
- Wired the `autofix` agent type into the control plane — agent runs now return a real
  diagnosis instead of a "not wired" placeholder.
- 15-test suite covering the rule table, file extraction, determinism, and API wiring.

### Added — Autofix: closing the loop
- Autofix daemon now commits real patches: `commit_file_changes` builds a commit via the
  GitHub Git Data API (blob → tree → commit → ref), so opened PRs contain the proposed fix
  instead of an empty diff. `diagnose` asks the LLM for full-file replacements; PRs open
  (status `pr_opened`) only when a target repo and a confident change are both present.
- Daemon falls back to the shared heuristic engine when no OpenRouter key is set (or the LLM
  call fails), so Sentry-sourced alerts get triaged instead of silently skipped. Heuristic
  diagnoses propose no code changes, so they never open a PR on their own.
- Demo sandbox gained an error-diagnosis panel (`/demo`): paste a stack trace, get severity,
  root cause, fix steps, and likely files from `/api/demo/diagnose` — no keys required.
- 8 tests covering the daemon commit/PR flow and heuristic fallback.

### Fixed
- Agent runs that completed successfully were recorded as `failed`; they now report `succeeded`.
- `swarm_build` emitted an About page with invalid JSX (`{{market.upper()}}`) that broke the
  generated project's build.

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
