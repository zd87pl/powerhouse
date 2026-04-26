# Wiki Schema

## Directory Structure

```
wiki/
├── index.md              ← Entry point
├── log.md                ← Decision & activity log
├── entities/             ← People, orgs, tools
│   └── flyio.md
├── concepts/             ← Abstract concepts
│   └── vector-db.md
├── comparisons/          ← Competitive analysis
│   └── competitor-landscape.md
├── projects/             ← Active & past projects
│   └── powerhouse-saas.md
├── decisions/            ← ADRs
│   └── ADR-001.md
├── queries/              ← Saved search patterns
│   └── how-to-debug-fly.md
└── raw/                  ← Unprocessed source material
    ├── papers/
    └── transcripts/
```

## Indexing Pipeline

1. Raw content downloaded to `raw/`
2. Extracted and summarized into entity/concept pages
3. All pages indexed into ChromaDB collection `wiki`
4. Semantic search available via `infra/scripts/index-wiki.sh`

## Query Interface

```python
import chromadb
client = chromadb.HttpClient(host="localhost", port=8001)
collection = client.get_collection("wiki")
results = collection.query(query_texts=["How does tenant isolation work?"], n_results=3)
```
