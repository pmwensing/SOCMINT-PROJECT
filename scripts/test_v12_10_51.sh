#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/baseline_aware_db_smoke_gate_v12_10_51.py
python -m pytest -q tests/test_v12_10_51_baseline_aware_db_smoke_gate.py
python scripts/baseline_aware_db_smoke_gate_v12_10_51.py

echo "[+] v12.10.51 baseline-aware DB smoke gate passed"
