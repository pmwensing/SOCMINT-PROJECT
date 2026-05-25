#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/repair_identity_columns_v12_10_45.py
python -m pytest -q tests/test_v12_10_45_identity_columns_repair.py

python scripts/repair_identity_columns_v12_10_45.py

# Rerun smoke/gates. Still safe if HOLD remains.
python scripts/db_migration_smoke_v12_10_38.py || true
python scripts/db_smoke_result_gate_v12_10_39.py || true
python scripts/db_smoke_exact_failure_locator_v12_10_42.py || true
python scripts/iterative_db_smoke_repair_loop_v12_10_44.py || true

python - <<'PY'
import json
from pathlib import Path

repair = json.loads(Path("release/db_smoke_identity_columns_repair/IDENTITY_COLUMNS_REPAIR_V12_10_45.json").read_text())
smoke = json.loads(Path("release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json").read_text())
gate = json.loads(Path("release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json").read_text())
loop = json.loads(Path("release/db_smoke_repair_loop/ITERATIVE_DB_SMOKE_REPAIR_LOOP_V12_10_44.json").read_text())

assert repair["production_db_touched"] is False
assert repair["real_config_upgrade_run"] is False
assert smoke["production_db_touched"] is False
assert smoke["real_config_upgrade_run"] is False
assert gate["production_db_touched"] is False
assert gate["real_config_upgrade_run"] is False
assert loop["production_db_touched"] is False
assert loop["real_config_upgrade_run"] is False

print("[+] v12.10.45 identity_columns repair complete")
print("[+] smoke_status:", smoke["smoke_status"])
print("[+] gate_release_status:", gate["release_status"])
print("[+] loop_final_status:", loop["final_status"])
print("[+] probable_failing_table:", loop["final"].get("probable_failing_table"))
PY
