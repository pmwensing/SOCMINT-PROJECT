#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/runtime_app_discovery_report_v12_10_54D.py
python -m pytest -q tests/test_v12_10_54D_runtime_app_discovery_adapter.py
python -m pytest -q tests/test_v12_10_54_runtime_hardening.py
python -m pytest -q tests/test_v12_10_54E_report_import_path_hard_fix.py

python scripts/runtime_app_discovery_report_v12_10_54D.py
python scripts/release_archive_integrity_v12_10_54.py
python scripts/tag_verification_report_v12_10_54.py || true
python scripts/post_release_runtime_hardening_report_v12_10_54.py

echo "[+] v12.10.54E report import path hard fix passed"
