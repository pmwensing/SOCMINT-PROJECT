#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/final_tag_manifest_head_sync_v12_10_53B.py
python -m pytest -q tests/test_v12_10_53B_final_tag_manifest_head_sync.py
python scripts/final_tag_manifest_head_sync_v12_10_53B.py

echo "[+] v12.10.53B final tag manifest HEAD sync passed"
