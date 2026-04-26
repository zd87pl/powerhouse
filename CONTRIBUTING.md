# 🤝 Contributing to Powerhouse

Thanks for your interest! This is an early-stage project with a lot of surface area. Here's how to help.

## Quick Start for Contributors

```bash
git clone https://github.com/zd87pl/powerhouse.git
cd powerhouse
cp infra/bootstrap/.envrc.example infra/bootstrap/.envrc
# Fill in your keys
source infra/bootstrap/.envrc
./infra/bootstrap/bootstrap-clis.sh
./infra/scripts/start-services.sh
```

## Good First Issues

| Issue | Difficulty | Impact |
|-------|-----------|--------|
| Add LiteLLM proxy to docker-compose | Easy | Cost savings |
| Write `powerhouse` CLI wrapper | Medium | UX |
| Stripe webhook handler | Medium | Revenue |
| Landing page with stitch-mcp | Medium | Growth |
| Real embeddings in index-wiki.sh | Easy | Search quality |
| GitHub App instead of PAT | Hard | Security |

## PR Guidelines

1. **One change per PR**
2. **No secrets ever** — CI will reject `.env` files
3. **Type hints** on all Python code
4. **Tests** for new logic
5. **Update docs** if you change architecture

Run checks locally:
```bash
ruff check services/
mypy services/ --ignore-missing-imports
shellcheck infra/**/*.sh
```

## Code Style

- Python: Black-compatible, typed, docstrings
- Bash: `set -euo pipefail`, shellchecked
- Docker: Multi-stage builds, non-root users
- Markdown: 80-char wrap, semantic line breaks

## Discussion

- 💡 Ideas → [GitHub Discussions](https://github.com/zd87pl/powerhouse/discussions)
- 🐛 Bugs → [GitHub Issues](https://github.com/zd87pl/powerhouse/issues)
- 🔒 Security → Email ziggy@powerhouse.dev (PGP key in repo)

## Philosophy

- **Batteries included** — One command should get you running
- **Explicit over implicit** — No magic; config over convention
- **Secure by default** — Secrets vault, egress allowlists, audit logs
- **Open source forever** — MIT license, no rug pull

---

*Let's build the future of software engineering together.*
