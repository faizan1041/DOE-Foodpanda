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
python3 -c "import fastapi, uvicorn, playwright" 2>/dev/null || {
    echo "Installing Python dependencies..."
    pip install fastapi uvicorn playwright 2>/dev/null || pip3 install fastapi uvicorn playwright
}

# Check Playwright browsers
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    p.chromium.executable_path
" 2>/dev/null || {
    echo "Installing Playwright browsers..."
    python3 -m playwright install chromium
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
echo "  The bot will open Foodpanda in a headless"
echo "  browser to find food options for you."
echo ""

cd execution
python3 foodpanda_server.py
