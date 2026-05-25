#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/post_commit_package_refresh_v12_10_53A.py
python -m pytest -q tests/test_v12_10_53A_post_commit_package_refresh.py
python scripts/post_commit_package_refresh_v12_10_53A.py

echo "[+] v12.10.53A post-commit package refresh + tag-ready verification passed"
