#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/restore_dashboard_safe_hook_v12_10_54C.py
python scripts/restore_dashboard_safe_hook_v12_10_54C.py

python -m py_compile src/socmint/dashboard.py
python -m pytest -q tests/test_v12_10_54C_restore_dashboard_safe_hook.py
python -m pytest -q tests/test_v12_10_54_runtime_hardening.py

python scripts/release_archive_integrity_v12_10_54.py
python scripts/tag_verification_report_v12_10_54.py || true
python scripts/post_release_runtime_hardening_report_v12_10_54.py

echo "[+] v12.10.54C restore dashboard + safe hook passed"
