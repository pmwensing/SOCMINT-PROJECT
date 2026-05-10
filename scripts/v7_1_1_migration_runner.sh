#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] SOCMINT v7.1.1 — Deployment DB resolver"

if [ -f .env ]; then
  set +u
  set -a
  . ./.env
  set +a
  set -u
fi

echo "[+] Resolve DB URL"
python3 -m socmint.deployment_db resolve --json

echo "[+] Write deployment override"
python3 -m socmint.deployment_db write-env --output .env.deployment.local

echo "[+] Alembic dry run"
python3 -m socmint.deployment_db dry-run

echo "[+] To run real migration when DB is reachable:"
echo "    PYTHONPATH=\$PWD/src python3 -m socmint.deployment_db migrate"
