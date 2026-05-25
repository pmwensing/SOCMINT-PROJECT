#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/model_migration_reconciliation_audit_v12_10_32.py
python -m pytest -q tests/test_v12_10_32_model_migration_reconciliation.py
python scripts/model_migration_reconciliation_audit_v12_10_32.py

echo "[+] v12.10.32 model/migration reconciliation audit passed"
