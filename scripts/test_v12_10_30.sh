#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

bash scripts/fix_v12_10_30_alembic_head.sh
python -m pytest -q tests/test_v12_10_30_alembic_head.py
bash scripts/test_v12_10_30_true_bootstrap.sh
bash scripts/test_v12_10_29.sh

echo "[+] v12.10.30 tests passed"
