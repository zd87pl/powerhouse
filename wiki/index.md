# Powerhouse Wiki

Welcome to the persistent knowledge base for Powerhouse.

## Quick Links

- [Schema](SCHEMA.md) — How this wiki is organized
- [Architecture](../docs/architecture.md) — System design
- [Roadmap](../docs/roadmap.md) — Development phases
- [ADRs](../docs/adrs/) — Architecture decisions

## How to Query

```bash
# Re-index after adding content
../infra/scripts/index-wiki.sh

# Query via Python
python3 -c "
import requests
r = requests.post('http://localhost:8001/api/v1/collections/wiki/query',
    json={'query_texts': ['tenant isolation'], 'n_results': 3})
print(r.json())
"
```

## Content Rules

1. One concept per file in `concepts/`
2. One entity per file in `entities/`
3. All decisions go in `decisions/` with ADR format
4. Raw sources stay in `raw/` — never edit directly, extract to structured pages
5. Cross-link with relative Markdown links
