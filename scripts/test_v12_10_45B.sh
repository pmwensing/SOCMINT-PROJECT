#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/repair_blocked_identity_tables_v12_10_45B.py
python -m pytest -q tests/test_v12_10_45B_blocked_identity_table_repair.py

python scripts/repair_blocked_identity_tables_v12_10_45B.py

# Rerun DB smoke/gates.
python scripts/db_migration_smoke_v12_10_38.py || true
python scripts/db_smoke_result_gate_v12_10_39.py || true
python scripts/db_smoke_exact_failure_locator_v12_10_42.py || true

python - <<'PY'
import json
from pathlib import Path

repair = json.loads(Path("release/blocked_identity_table_repair/BLOCKED_IDENTITY_TABLE_REPAIR_V12_10_45B.json").read_text())
smoke = json.loads(Path("release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json").read_text())
gate = json.loads(Path("release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json").read_text())
locator = json.loads(Path("release/db_smoke_exact_failure/DB_SMOKE_EXACT_FAILURE_LOCATOR_V12_10_42.json").read_text())

assert repair["production_db_touched"] is False
assert repair["real_config_upgrade_run"] is False
assert smoke["production_db_touched"] is False
assert smoke["real_config_upgrade_run"] is False
assert gate["production_db_touched"] is False
assert gate["real_config_upgrade_run"] is False

print("[+] v12.10.45B repair complete")
print("[+] smoke_status:", smoke["smoke_status"])
print("[+] gate_release_status:", gate["release_status"])
print("[+] probable_failing_table:", locator.get("probable_failing_table"))
print("[+] missing_after_upgrade:", len(smoke.get("missing_after_upgrade", [])))
print("[+] lingering_after_downgrade:", len(smoke.get("lingering_after_downgrade", [])))
PY
