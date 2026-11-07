#!/usr/bin/env bash
# ==============================================================================
# Polymarket 24/7 Cloud Bot Automated Setup Script
# Works on Ubuntu 20.04 / 22.04 / 24.04 & Debian
# ==============================================================================

set -e

echo "🚀 [1/4] Updating system packages..."
apt-get update -y && apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv git curl

echo "🐳 [2/4] Installing Docker and Docker Compose (Optional / Recommended)..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

echo "📦 [3/4] Setting up Python Virtual Environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "⚙️ [4/4] Creating logs directory..."
mkdir -p logs

echo "=================================================================="
echo "✅ Cloud Bot Setup Complete!"
echo "=================================================================="
echo ""
echo "Next Steps:"
echo "1. Edit your .env file:        nano .env"
echo "2. Edit your trading rules:   nano config/trading_rules.json"
echo "3. Run a test dry-run:        python3 run.py --test-rules"
echo ""
echo "To run 24/7 in background with Docker:"
echo "   docker compose -f deploy/docker-compose.yml up -d --build"
echo ""
echo "To view live 24/7 logs:"
echo "   docker logs -f polymarket-24-7-bot"
echo "=================================================================="
