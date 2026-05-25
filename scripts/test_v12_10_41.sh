#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/repair_0018_todo_placeholders_v12_10_41.py
python -m pytest -q tests/test_v12_10_41_todo_repair.py

python scripts/repair_0018_todo_placeholders_v12_10_41.py

# Rerun temp SQLite DB smoke and gate. These may still NO-GO for a different reason,
# but real DB must not be touched.
python scripts/db_migration_smoke_v12_10_38.py || true
python scripts/db_smoke_result_gate_v12_10_39.py || true

python - <<'PY'
import json
from pathlib import Path

repair = json.loads(Path("release/db_smoke_repair/TODO_PLACEHOLDER_REPAIR_V12_10_41.json").read_text())
smoke = json.loads(Path("release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json").read_text())
gate = json.loads(Path("release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json").read_text())

assert repair["repair_status"] == "GO"
assert repair["production_db_touched"] is False
assert repair["real_config_upgrade_run"] is False
assert smoke["production_db_touched"] is False
assert smoke["real_config_upgrade_run"] is False
assert gate["production_db_touched"] is False
assert gate["real_config_upgrade_run"] is False

print("[+] v12.10.41 repair complete")
print("[+] smoke_status:", smoke["smoke_status"])
print("[+] gate_release_status:", gate["release_status"])
PY
