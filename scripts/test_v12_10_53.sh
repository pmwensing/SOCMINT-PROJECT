#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/release_package_tag_manifest_v12_10_53.py
python -m pytest -q tests/test_v12_10_53_release_package_tag_manifest.py
python scripts/release_package_tag_manifest_v12_10_53.py

echo "[+] v12.10.53 release package + tag manifest passed"
