#!/bin/bash
# =============================================================================
# Stop all Powerhouse core services
# =============================================================================
set -euo pipefail

echo "🛑 Stopping Powerhouse services..."
cd "$(dirname "$0")/.."
docker compose -f docker-compose.yml down

echo "✅ All services stopped."
echo ""
echo "Data preserved at /data/powerhouse/"
