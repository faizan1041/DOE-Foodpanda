#!/bin/bash
# DOE Foodpanda Agent - Start Script
#
# Usage:
#   ./start_foodpanda.sh
#
# Environment variables (set in .env or export):
#   FOODPANDA_PORT=8422    # Web UI port

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Load .env if present
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Ensure .tmp directory exists
mkdir -p .tmp

# Check dependencies
echo "Checking dependencies..."
python3 -c "import fastapi, uvicorn, httpx, anthropic, apscheduler" 2>/dev/null || {
    echo "Installing Python dependencies..."
    pip install -r requirements.txt 2>/dev/null || pip3 install -r requirements.txt
}

PORT=${FOODPANDA_PORT:-8422}

echo ""
echo "  =================================="
echo "  DOE Foodpanda Agent"
echo "  =================================="
echo ""
echo "  Chat UI:   http://localhost:$PORT"
echo "  API:       http://localhost:$PORT/api/chat"
echo ""
echo "  Daily lunch search: 12:30 PM PKT"
echo "  Desktop notifications enabled"
echo ""

cd execution
python3 foodpanda_server.py
