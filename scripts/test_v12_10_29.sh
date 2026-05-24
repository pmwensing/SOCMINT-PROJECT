#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

echo "[+] Compile v12.10.29 modules"
python -m py_compile \
  src/socmint/v12_10_command_center.py \
  src/socmint/v12_10_command_center_routes.py \
  src/socmint/v12_10_29_ui.py

echo "[+] Run command center unit tests"
python -m pytest -q tests/test_v12_10_command_center.py

echo "[+] Run route discovery tests"
python -m pytest -q tests/test_v12_10_29_routes.py

echo "[+] Run clean-bootstrap validation"
bash scripts/test_v12_10_29_clean_bootstrap.sh

echo "[+] v12.10.29 tests passed"
