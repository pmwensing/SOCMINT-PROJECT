#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.10.30 true Alembic bootstrap validation"

python - <<'PY'
from pathlib import Path
import configparser
import importlib.util
import subprocess

cfg = configparser.ConfigParser()
cfg.read("alembic.ini")
loc = cfg.get("alembic", "script_location", fallback="alembic")
migration = Path(loc) / "versions" / "0017_v12_10_schema_reconciliation.py"

print("script_location =", loc)
print("migration       =", migration)

assert migration.exists(), f"missing migration {migration}"

spec = importlib.util.spec_from_file_location("mig0017", migration)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print("revision      =", mod.revision)
print("down_revision =", mod.down_revision)

assert mod.revision == "0017_v12_10_schema_reconciliation"
assert isinstance(mod.down_revision, str)
assert len(mod.down_revision) > 0

heads_out = subprocess.check_output(["alembic", "heads"], text=True)
heads = [line.split()[0] for line in heads_out.splitlines() if line.strip()]
print("heads =", heads)
assert heads == ["0017_v12_10_schema_reconciliation"], heads

text = migration.read_text()
for table in [
    "dossier_exports",
    "evidence_hash_events",
    "intel_runs",
    "analyst_decisions",
    "strategic_risk_scores",
    "continuous_monitoring_events",
]:
    assert table in text, f"missing table: {table}"

print("[+] active 0017 migration imports and is sole head")
PY

echo "[+] v12.10.30 true bootstrap validation passed"
