#!/usr/bin/env bash
set -e

echo "========================================"
echo " Stock Analysis - Starting..."
echo "========================================"

# Kill any process already listening on port 5000
if lsof -Pi :5000 -sTCP:LISTEN -t &>/dev/null; then
    echo "  Killing old server on port 5000..."
    lsof -Pi :5000 -sTCP:LISTEN -t | xargs kill -9
    sleep 1
fi

# Create venv if missing
if [ ! -f "venv/bin/python" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Install / update packages
echo "Installing packages..."
venv/bin/python -m pip install -r requirements.txt -q

# Create .env from example if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo ""
    echo "[INFO] .env created from template. Set ANTHROPIC_API_KEY to enable AI analysis."
    echo ""
fi

echo ""
echo "Server starting at: http://127.0.0.1:5000"
echo "Press Ctrl+C to stop."
echo ""

venv/bin/python app.py
