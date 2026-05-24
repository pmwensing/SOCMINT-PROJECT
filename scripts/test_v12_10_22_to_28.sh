#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-$PWD}"
python -m pytest -q tests/test_v12_10_command_center.py
python -m py_compile \
  src/socmint/v12_10_command_center.py \
  src/socmint/v12_10_command_center_routes.py
echo "[+] v12.10.22 → v12.10.28 tests passed"
