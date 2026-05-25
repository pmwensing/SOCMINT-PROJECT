#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/existing_table_collision_guard_v12_10_49.py
python -m pytest -q tests/test_v12_10_49_existing_table_collision_guard.py

python scripts/existing_table_collision_guard_v12_10_49.py

python scripts/db_migration_smoke_v12_10_38.py || true
python scripts/db_smoke_result_gate_v12_10_39.py || true
python scripts/full_db_smoke_trace_capture_v12_10_48.py || true

python - <<'PY'
import json
from pathlib import Path

guard = json.loads(Path("release/existing_table_collision_guard/EXISTING_TABLE_COLLISION_GUARD_V12_10_49.json").read_text())
smoke = json.loads(Path("release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json").read_text())
gate = json.loads(Path("release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json").read_text())
trace = json.loads(Path("release/full_db_smoke_trace/FULL_DB_SMOKE_TRACE_CAPTURE_V12_10_48.json").read_text())

assert guard["production_db_touched"] is False
assert guard["real_config_upgrade_run"] is False
assert smoke["production_db_touched"] is False
assert smoke["real_config_upgrade_run"] is False
assert gate["production_db_touched"] is False
assert gate["real_config_upgrade_run"] is False
assert trace["production_db_touched"] is False
assert trace["real_config_upgrade_run"] is False

print("[+] v12.10.49 collision guard complete")
print("[+] collision_tables:", guard["collision_tables"])
print("[+] smoke_status:", smoke["smoke_status"])
print("[+] gate_release_status:", gate["release_status"])
print("[+] latest_exception:", trace["exception"]["exact_exception"])
PY
