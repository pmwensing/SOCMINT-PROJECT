#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/final_release_readiness_manifest_v12_10_52.py
python -m pytest -q tests/test_v12_10_52_final_release_readiness.py
python scripts/final_release_readiness_manifest_v12_10_52.py

echo "[+] v12.10.52 final release readiness passed"
