#!/usr/bin/env bash
# Lightweight helper to run the backend with PYTHONPATH set so `import app` works.
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$script_dir"
cd "$script_dir"
echo "Starting backend from: $script_dir"
python -m uvicorn app.main:app --reload --port 8000 --log-level debug
