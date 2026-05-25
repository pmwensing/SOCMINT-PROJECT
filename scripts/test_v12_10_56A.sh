#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile \
  src/socmint/wsgi.py \
  src/socmint/v12_10_56_production_entrypoint.py \
  scripts/production_entrypoint_route_lock_report_v12_10_56.py

python -m pytest -q tests/test_v12_10_56A_production_wsgi_entrypoint_shim.py
python -m pytest -q tests/test_v12_10_56_production_entrypoint_route_lock.py
python -m pytest -q tests/test_v12_10_55_real_runtime_route_mount.py
python -m pytest -q tests/test_v12_10_54G_discovery_report_fallback_probe.py
python -m pytest -q tests/test_v12_10_54_runtime_hardening.py

python scripts/production_entrypoint_route_lock_report_v12_10_56.py
python scripts/post_release_runtime_hardening_report_v12_10_54.py
python scripts/real_db_upgrade_guard_v12_10_54.py || true

echo "[+] v12.10.56A production WSGI entrypoint shim passed"
