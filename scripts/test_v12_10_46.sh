#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/exact_alembic_exception_diagnostic_v12_10_46.py
python -m pytest -q tests/test_v12_10_46_exact_alembic_exception_diagnostic.py
python scripts/exact_alembic_exception_diagnostic_v12_10_46.py

echo "[+] v12.10.46 exact Alembic exception diagnostic passed"
