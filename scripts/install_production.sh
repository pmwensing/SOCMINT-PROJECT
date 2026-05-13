#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${SOCMINT_ENV_FILE:-.env.production}"
TEMPLATE=".env.production.example"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[!] Missing required command: $1" >&2
    exit 1
  }
}

echo "[+] SOCMINT production installer v10.2.0"
require_cmd python3
require_cmd make

if [ ! -f "$ENV_FILE" ]; then
  if [ ! -f "$TEMPLATE" ]; then
    echo "[!] Missing $TEMPLATE" >&2
    exit 1
  fi
  cp "$TEMPLATE" "$ENV_FILE"
  echo "[+] Created $ENV_FILE from template"
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

python3 -m venv "${SOCMINT_VENV:-venv}"
# shellcheck disable=SC1091
source "${SOCMINT_VENV:-venv}/bin/activate"
python -m pip install --upgrade pip

if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
elif [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  pip install -e ".[dev]" || pip install -e .
fi

if command -v alembic >/dev/null 2>&1; then
  alembic upgrade head
else
  make migrate
fi

if [ -n "${SOCMINT_ADMIN_USER:-}" ] && [ -n "${SOCMINT_ADMIN_PASSWORD:-}" ]; then
  python -m src.socmint.main init-admin "$SOCMINT_ADMIN_USER" "$SOCMINT_ADMIN_PASSWORD" || true
fi

make backup-restore-smoke
make production-smoke

echo "[+] Production installer complete"
echo "[+] Start app with: set -a; source $ENV_FILE; set +a; make serve"
