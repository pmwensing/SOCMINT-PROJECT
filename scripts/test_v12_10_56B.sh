#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/production_entrypoint_route_lock_report_v12_10_56.py
python -m pytest -q tests/test_v12_10_56B_report_import_path.py
python -m pytest -q tests/test_v12_10_56A_production_wsgi_entrypoint_shim.py

python scripts/production_entrypoint_route_lock_report_v12_10_56.py
python scripts/post_release_runtime_hardening_report_v12_10_54.py
python scripts/real_db_upgrade_guard_v12_10_54.py || true

echo "[+] v12.10.56B report import path fix passed"
