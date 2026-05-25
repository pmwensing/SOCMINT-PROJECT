#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/final_readiness_optional_demote_v12_10_52A.py
python -m pytest -q tests/test_v12_10_52A_final_readiness_optional_demote.py
python scripts/final_readiness_optional_demote_v12_10_52A.py

echo "[+] v12.10.52A corrected final release readiness passed"
