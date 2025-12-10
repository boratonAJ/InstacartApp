#!/usr/bin/env bash
set -euo pipefail
# One-button runner for the Flask app.
# Usage: `bash run.sh` or `./run.sh` (make executable with `chmod +x run.sh`).

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# Load .env file if present (allows quick local overrides).
if [ -f .env ]; then
  echo "Loading environment variables from .env"
  set -o allexport
  # shellcheck disable=SC1091
  . .env
  set +o allexport
fi

# Prefer python3.10 if available
PY=python3.10
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python3
fi

if [ ! -d .venv ]; then
  echo "Creating virtual environment with $PY..."
  "$PY" -m venv .venv
fi

echo "Activating virtualenv..."
. .venv/bin/activate

echo "Upgrading pip and installing requirements..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

if [ -z "${FINAL_INSTACART_DB:-}" ]; then
  echo "No FINAL_INSTACART_DB env var set — using default ../final_instacart.db"
else
  echo "Using FINAL_INSTACART_DB=${FINAL_INSTACART_DB}"
fi

echo "Starting Flask app (press Ctrl-C to stop)..."
exec python app.py
