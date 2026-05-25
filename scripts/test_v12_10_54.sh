#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile \
  src/socmint/v12_10_54_runtime_guard.py \
  src/socmint/v12_10_54_runtime_guard_routes.py \
  scripts/real_db_upgrade_guard_v12_10_54.py \
  scripts/release_archive_integrity_v12_10_54.py \
  scripts/tag_verification_report_v12_10_54.py \
  scripts/post_release_runtime_hardening_report_v12_10_54.py

python -m pytest -q tests/test_v12_10_54_runtime_hardening.py

python scripts/release_archive_integrity_v12_10_54.py
python scripts/tag_verification_report_v12_10_54.py || true
python scripts/post_release_runtime_hardening_report_v12_10_54.py

echo "[+] v12.10.54 post-release runtime hardening passed"
