#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/identity_constraint_neutralizer_v12_10_47.py
python -m pytest -q tests/test_v12_10_47_identity_constraint_neutralizer.py

python scripts/identity_constraint_neutralizer_v12_10_47.py

# Rerun temp smoke and gates. Real DB still untouched.
python scripts/db_migration_smoke_v12_10_38.py || true
python scripts/db_smoke_result_gate_v12_10_39.py || true
python scripts/db_smoke_exact_failure_locator_v12_10_42.py || true

python - <<'PY'
import json
from pathlib import Path

neutral = json.loads(Path("release/identity_constraint_neutralizer/IDENTITY_CONSTRAINT_NEUTRALIZER_V12_10_47.json").read_text())
smoke = json.loads(Path("release/db_migration_smoke/DB_MIGRATION_SMOKE_V12_10_38.json").read_text())
gate = json.loads(Path("release/db_smoke_gate/DB_SMOKE_RESULT_GATE_V12_10_39.json").read_text())
locator = json.loads(Path("release/db_smoke_exact_failure/DB_SMOKE_EXACT_FAILURE_LOCATOR_V12_10_42.json").read_text())

assert neutral["production_db_touched"] is False
assert neutral["real_config_upgrade_run"] is False
assert smoke["production_db_touched"] is False
assert smoke["real_config_upgrade_run"] is False
assert gate["production_db_touched"] is False
assert gate["real_config_upgrade_run"] is False

print("[+] v12.10.47 neutralizer complete")
print("[+] smoke_status:", smoke["smoke_status"])
print("[+] gate_release_status:", gate["release_status"])
print("[+] probable_failing_table:", locator.get("probable_failing_table"))
print("[+] missing_after_upgrade:", len(smoke.get("missing_after_upgrade", [])))
print("[+] lingering_after_downgrade:", len(smoke.get("lingering_after_downgrade", [])))
PY
