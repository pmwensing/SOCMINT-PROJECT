#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/validate_approved_migration_draft_v12_10_36.py
python -m pytest -q tests/test_v12_10_36_approved_draft_static_validator.py
python scripts/validate_approved_migration_draft_v12_10_36.py

echo "[+] v12.10.36 approved draft static validator passed"
