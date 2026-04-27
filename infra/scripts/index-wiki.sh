#!/bin/bash
# =============================================================================
# Index wiki content into ChromaDB
# =============================================================================
set -euo pipefail

echo "🧠 Indexing wiki into ChromaDB..."

CHROMA_URL="http://localhost:8001"
WIKI_DIR="/data/powerhouse/wiki"

# Check ChromaDB is running
if ! curl -sf "$CHROMA_URL/api/v2/heartbeat" > /dev/null 2>&1; then
    echo "❌ ChromaDB not running at $CHROMA_URL"
    echo "   Start with: ./start-services.sh"
    exit 1
fi

# Python index script (uses ChromaDB v1 API — update to v2 if running latest ChromaDB)
python3 << 'PYEOF'
import os, glob, json, requests
from pathlib import Path

CHROMA = "http://localhost:8001"
WIKI = Path("/data/powerhouse/wiki")

# Ensure collection exists
coll_resp = requests.post(f"{CHROMA}/api/v1/collections", json={"name": "wiki"})
if coll_resp.status_code == 409:
    pass  # already exists
elif coll_resp.status_code not in (200, 201):
    print(f"Collection create failed: {coll_resp.text}")
    exit(1)

# Simple keyword-based "embedding" for now (replace with real embeddings later)
# This establishes the indexing pipeline.
docs = []
metas = []
ids = []

for md in WIKI.rglob("*.md"):
    text = md.read_text(encoding="utf-8")
    doc_id = str(md.relative_to(WIKI)).replace("/", "_").replace(" ", "_")
    docs.append(text)
    metas.append({"source": str(md), "title": md.stem})
    ids.append(doc_id)

# Also index raw papers
papers_dir = Path("/data/powerhouse/wiki/raw/papers")
if papers_dir.exists():
    for md in papers_dir.glob("*.md"):
        text = md.read_text(encoding="utf-8")
        doc_id = f"paper_{md.stem}"
        docs.append(text)
        metas.append({"source": str(md), "type": "arxiv"})
        ids.append(doc_id)

if not docs:
    print("⚠️  No markdown files found in wiki/")
    exit(0)

# Add to ChromaDB
add_resp = requests.post(
    f"{CHROMA}/api/v1/collections/wiki/documents",
    json={"documents": docs, "metadatas": metas, "ids": ids}
)
if add_resp.status_code not in (200, 201):
    print(f"Index failed: {add_resp.text}")
    exit(1)

print(f"✅ Indexed {len(docs)} documents into ChromaDB")
PYEOF

echo "Done!"
