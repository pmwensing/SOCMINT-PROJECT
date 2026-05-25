#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/db_smoke_exact_failure_locator_v12_10_42.py
python -m pytest -q tests/test_v12_10_42_db_smoke_exact_failure_locator.py
python scripts/db_smoke_exact_failure_locator_v12_10_42.py

echo "[+] v12.10.42 exact failure locator passed"
