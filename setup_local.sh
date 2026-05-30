#!/usr/bin/env bash
# =============================================================
# setup_local.sh — One-command local environment setup
# Azure Healthcare Analytics Platform
# =============================================================
set -euo pipefail

echo ""
echo "======================================================"
echo "  Azure Healthcare Analytics Platform — Local Setup"
echo "======================================================"
echo ""

# ── Check prerequisites ──────────────────────────────────────
check_command() {
  if ! command -v "$1" &>/dev/null; then
    echo "❌  Missing: $1 — please install it first."
    exit 1
  else
    echo "✅  Found: $1 ($(command -v "$1"))"
  fi
}

echo "Checking prerequisites..."
check_command python3
check_command java
check_command git

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
JAVA_VERSION=$(java -version 2>&1 | head -1)
echo ""
echo "  Python : $PYTHON_VERSION"
echo "  Java   : $JAVA_VERSION"
echo ""

# ── Virtual environment ──────────────────────────────────────
echo "Creating virtual environment..."
python3 -m venv .venv
echo "✅  Virtual environment created at .venv/"

# Activate
source .venv/bin/activate
echo "✅  Activated"

# ── Install dependencies ─────────────────────────────────────
echo ""
echo "Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements-dev.txt -q
echo "✅  Dependencies installed"

# ── Generate sample data ─────────────────────────────────────
echo ""
echo "Generating synthetic healthcare sample data..."
cd sample-data
python3 generate_data.py
cd ..
echo "✅  Sample data ready in sample-data/"

# ── Run unit tests ───────────────────────────────────────────
echo ""
echo "Running unit tests (no Spark required)..."
pytest tests/unit/ tests/data_quality/ -v --tb=short
echo "✅  Unit tests passed"

# ── Done ─────────────────────────────────────────────────────
echo ""
echo "======================================================"
echo "  Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Activate environment:  source .venv/bin/activate"
echo "  2. Run all tests:         pytest tests/ -v"
echo "  3. Deploy to Azure:       see README.md → Deploy to Azure"
echo "  4. Push to GitHub:        see README.md → Push to GitHub"
echo "======================================================"
echo ""
