#!/bin/bash
# =============================================================================
# Start all Powerhouse core services
# =============================================================================
set -euo pipefail

echo "🚀 Powerhouse Service Startup"
echo "   Data dir: /data/powerhouse"
echo ""

# ─── Ensure data directories exist ──────────────────────────────────────────
mkdir -p /data/powerhouse/{chroma-data,n8n-data/.n8n,observability-bridge,wiki,projects,orchestrator/runs}

# ─── Start via Docker Compose ───────────────────────────────────────────────
cd "$(dirname "$0")/.."
docker compose -f docker-compose.yml up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# ─── Health checks ──────────────────────────────────────────────────────────
if curl -sf http://localhost:8001/api/v2/heartbeat > /dev/null 2>&1; then
    echo "✅ ChromaDB: http://localhost:8001"
else
    echo "⚠️  ChromaDB: not responding yet (may need more time)"
fi

if curl -sf http://localhost:5678/rest/health > /dev/null 2>&1; then
    echo "✅ n8n: http://localhost:5678"
else
    echo "⚠️  n8n: not responding yet (may need more time)"
fi

echo ""
echo "🎉 Done!"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f chromadb    → watch ChromaDB logs"
echo "  docker compose logs -f n8n         → watch n8n logs"
echo "  ./stop-services.sh                  → stop everything"
