#!/usr/bin/env bash
set -euo pipefail

echo "[+] v12.10.29 clean-bootstrap validation"
echo "[+] Delegating Alembic head validation to v12.10.30 true bootstrap rules"

if [ -x scripts/test_v12_10_30_true_bootstrap.sh ]; then
  bash scripts/test_v12_10_30_true_bootstrap.sh
else
  python - <<'PY'
from pathlib import Path
import configparser
import importlib.util

cfg = configparser.ConfigParser()
cfg.read("alembic.ini")
loc = cfg.get("alembic", "script_location", fallback="alembic")
migration = Path(loc) / "versions" / "0017_v12_10_schema_reconciliation.py"

assert migration.exists(), f"missing migration: {migration}"

spec = importlib.util.spec_from_file_location("mig0017", migration)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

assert mod.revision == "0017_v12_10_schema_reconciliation"
assert mod.down_revision

print("[+] migration static bootstrap check passed")
PY
fi
