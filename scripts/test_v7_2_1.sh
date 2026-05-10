#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

if [ -f .env ]; then
  set +u
  set -a
  . ./.env
  set +a
  set -u
fi

echo "[+] Compile"
python3 -m compileall -q src/socmint

echo "[+] Review decision status"
./scripts/review_decisions_status.sh

echo "[+] Tests"
pytest -q tests/test_review_decisions_v7_2_1.py
