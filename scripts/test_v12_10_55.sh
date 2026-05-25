#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile \
  src/socmint/v12_10_55_runtime_mount.py \
  scripts/real_runtime_route_mount_report_v12_10_55.py

python -m py_compile src/socmint/dashboard.py

python -m pytest -q tests/test_v12_10_55_real_runtime_route_mount.py
python -m pytest -q tests/test_v12_10_54G_discovery_report_fallback_probe.py
python -m pytest -q tests/test_v12_10_54_runtime_hardening.py

python scripts/real_runtime_route_mount_report_v12_10_55.py
python scripts/runtime_app_discovery_report_v12_10_54D.py
python scripts/post_release_runtime_hardening_report_v12_10_54.py
python scripts/real_db_upgrade_guard_v12_10_54.py || true

echo "[+] v12.10.55 real runtime route mount verification passed"
