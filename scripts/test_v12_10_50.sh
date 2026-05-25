#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/downgrade_symmetry_repair_v12_10_50.py
python -m pytest -q tests/test_v12_10_50_downgrade_symmetry_repair.py

python scripts/downgrade_symmetry_repair_v12_10_50.py

python scripts/db_migration_smoke_v12_10_38.py || true
python scripts/db_smoke_result_gate_v12_10_39.py || true
python scripts/full_db_smoke_trace_capture_v12_10_48.py || true

python - <<'PY'
import json
from pathlib import Path

repair = json.loads(Path("release/downgrade_symmetry_repair/DOWNGRADE_SYMMETRY_REPAIR_V12_10_50.json").read_text())
smoke = json.loads(Path("release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json").read_text())
gate = json.loads(Path("release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json").read_text())
trace = json.loads(Path("release/full_db_smoke_trace/FULL_DB_SMOKE_TRACE_CAPTURE_V12_10_48.json").read_text())

assert repair["production_db_touched"] is False
assert repair["real_config_upgrade_run"] is False
assert smoke["production_db_touched"] is False
assert smoke["real_config_upgrade_run"] is False
assert gate["production_db_touched"] is False
assert gate["real_config_upgrade_run"] is False
assert trace["production_db_touched"] is False
assert trace["real_config_upgrade_run"] is False

print("[+] v12.10.50 downgrade symmetry repair complete")
print("[+] repair_status:", repair["repair_status"])
print("[+] smoke_status:", smoke["smoke_status"])
print("[+] gate_release_status:", gate["release_status"])
print("[+] lingering_after_downgrade:", len(smoke.get("lingering_after_downgrade", [])))
print("[+] missing_after_upgrade:", len(smoke.get("missing_after_upgrade", [])))
print("[+] latest_exception:", trace["exception"]["exact_exception"])
PY
