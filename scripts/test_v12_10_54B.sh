#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/fix_dashboard_compile_recovery_v12_10_54B.py
python scripts/fix_dashboard_compile_recovery_v12_10_54B.py

python -m py_compile src/socmint/dashboard.py
python -m pytest -q tests/test_v12_10_54B_dashboard_compile_recovery.py
python -m pytest -q tests/test_v12_10_54_runtime_hardening.py

python scripts/release_archive_integrity_v12_10_54.py
python scripts/tag_verification_report_v12_10_54.py || true
python scripts/post_release_runtime_hardening_report_v12_10_54.py

echo "[+] v12.10.54B dashboard compile recovery and runtime hardening tests passed"
