#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/fix_dashboard_route_registration_v12_10_54A.py
python scripts/fix_dashboard_route_registration_v12_10_54A.py

python -m py_compile src/socmint/dashboard.py
python -m pytest -q tests/test_v12_10_54A_dashboard_route_fix.py
python -m pytest -q tests/test_v12_10_54_runtime_hardening.py

python scripts/release_archive_integrity_v12_10_54.py
python scripts/tag_verification_report_v12_10_54.py || true
python scripts/post_release_runtime_hardening_report_v12_10_54.py

echo "[+] v12.10.54A dashboard route fix and runtime hardening tests passed"
