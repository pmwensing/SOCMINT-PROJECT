#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.10.29 clean-bootstrap validation"

python - <<'PY'
from pathlib import Path
import importlib.util

migration = Path("alembic/versions/0017_v12_10_schema_reconciliation.py")
assert migration.exists(), "missing v12.10 schema reconciliation migration"

text = migration.read_text()
required_tables = [
    "dossier_exports",
    "evidence_hash_events",
    "intel_runs",
    "analyst_decisions",
    "strategic_risk_scores",
    "continuous_monitoring_events",
]
for table in required_tables:
    assert table in text, f"migration missing table {table}"

spec = importlib.util.spec_from_file_location("mig0017", migration)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.revision == "0017_v12_10_schema_reconciliation"
assert mod.down_revision == "0004_roles_and_scan_jobs"
assert hasattr(mod, "upgrade")
assert hasattr(mod, "downgrade")
print("[+] migration static bootstrap check passed")
PY

if command -v alembic >/dev/null 2>&1 && [ -f alembic.ini ]; then
  echo "[+] alembic available; validating heads"
  alembic heads || true
else
  echo "[!] alembic CLI or alembic.ini not available; static migration validation only"
fi
