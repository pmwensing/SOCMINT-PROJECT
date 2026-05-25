#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/promote_approved_migration_v12_10_37.py
python -m pytest -q tests/test_v12_10_37_migration_promotion_gate.py

# Explicitly confirm we still did not run an upgrade.
python - <<'PY'
import json
from pathlib import Path

p = Path("release/migration_promotion/MIGRATION_PROMOTION_MANIFEST_V12_10_37.json")
data = json.loads(p.read_text())
assert data["schema_mutation"] == "none"
assert data["alembic_upgrade_run"] is False
assert data["promoted"] is True
assert data["alembic"]["expected_head_present"] is True
print("[+] v12.10.37 promotion manifest verified")
PY

echo "[+] v12.10.37 migration promotion gate passed"
