#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

REPORT_ROOT="var/socmint/rc_reports"
WORK_ROOT="var/test_v12_10_14"
VENV_DIR="$WORK_ROOT/.venv"
DB_PATH="$WORK_ROOT/socmint_v12_10_14.db"
DATA_DIR="$WORK_ROOT/data"
LOG_FILE="$WORK_ROOT/socmint.log"
STATUS_JSON="$REPORT_ROOT/socmint_v12_10_14_fresh_db_gate_status.json"
STATUS_MD="$REPORT_ROOT/socmint_v12_10_14_fresh_db_gate_status.md"

record_json() {
  local status="$1"
  local decision="$2"
  local message="$3"
  mkdir -p "$REPORT_ROOT"
  python3 - <<PY
import json
from datetime import UTC, datetime
payload = {
  "schema": "socmint.release.fresh_db_gate.v12_10_14",
  "version": "12.10.14",
  "generated_at": datetime.now(UTC).isoformat(),
  "status": "$status",
  "decision": "$decision",
  "message": "$message",
  "work_root": "$WORK_ROOT",
  "database_url": "sqlite:///$DB_PATH",
  "reports": {
    "status_json": "$STATUS_JSON",
    "status_markdown": "$STATUS_MD"
  }
}
open("$STATUS_JSON", "w").write(json.dumps(payload, indent=2, sort_keys=True))
PY
}

section() {
  echo
  echo "[+] $*"
  mkdir -p "$REPORT_ROOT"
  echo "## $*" >> "$STATUS_MD"
  echo >> "$STATUS_MD"
}

pass_line() {
  echo "PASS $*"
  echo "- PASS $*" >> "$STATUS_MD"
}

fail() {
  echo "FAIL $*" >&2
  mkdir -p "$REPORT_ROOT"
  echo "- FAIL $*" >> "$STATUS_MD"
  record_json "fail" "FAIL" "$*"
  exit 1
}

trap 'fail "fresh DB release gate aborted at line $LINENO"' ERR

# The clean-check must happen before this script creates var/ artifacts.
echo "[+] SOCMINT v12.10.14 Fresh DB Release Gate"
echo "[+] 1. git clean checkout"
git status --short
if [ -n "$(git status --short)" ]; then
  fail "working tree is not clean"
fi

rm -rf "$WORK_ROOT"
mkdir -p "$REPORT_ROOT" "$WORK_ROOT" "$DATA_DIR"
: > "$STATUS_MD"
section "SOCMINT v12.10.14 Fresh DB Release Gate"
section "1. git clean checkout"
pass_line "working tree clean"

section "2. python venv install succeeds"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
pass_line "editable install completed"

export PYTHONPATH="$ROOT/src:$ROOT"
export DATABASE_URL="sqlite:///$DB_PATH"
export SOCMINT_DATA_DIR="$DATA_DIR"
export SOCMINT_LOG_FILE="$LOG_FILE"
export SOCMINT_SECRET_KEY="test-v12-10-14-secret-key-000000000000000000000000"
export SOCMINT_AUTO_CREATE_DB=false
export SOCMINT_ALLOW_SIGNUP=false

section "3. pyproject version matches release manifest"
python - <<'PY'
import json
import re
from pathlib import Path
manifest = json.loads(Path("release/CURRENT_STATUS.json").read_text())
pyproject = Path("pyproject.toml").read_text()
match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
assert match, "pyproject version missing"
assert match.group(1) == manifest["version"], f"pyproject {match.group(1)} != manifest {manifest['version']}"
from socmint.version import VERSION
assert VERSION == manifest["version"], f"package VERSION {VERSION} != manifest {manifest['version']}"
print({"version": VERSION, "manifest": manifest["version"]})
PY
pass_line "version metadata aligned"

section "4. alembic upgrade head succeeds on empty DB"
rm -f "$DB_PATH"
alembic upgrade head
python - <<'PY'
from sqlalchemy import create_engine, inspect
import os
engine = create_engine(os.environ["DATABASE_URL"])
tables = set(inspect(engine).get_table_names())
required = {"spine_subjects", "spine_seeds", "spine_connector_runs", "spine_observations", "spine_dossier_assertions", "spine_validation_events"}
missing = sorted(required - tables)
assert not missing, f"missing tables after alembic: {missing}"
print({"table_count": len(tables), "required_present": sorted(required)})
PY
pass_line "alembic migration completed on empty SQLite DB"

export SOCMINT_AUTO_CREATE_DB=true

section "5-7. app import, route list, command_center_payload"
python scripts/runtime_route_release_gate_v12_10_14.py
pass_line "runtime route release gate passed"

section "8-15. subject-to-dossier E2E and RC report exports"
python scripts/subject_to_dossier_e2e_v12_10_14.py
pass_line "subject-to-dossier E2E release gate passed"

record_json "pass" "GO" "SOCMINT v12.10.14 fresh DB release gate passed"
cat >> "$STATUS_MD" <<EOF

## Result

- Status: \`pass\`
- Decision: \`GO\`
- JSON: \`$STATUS_JSON\`
- Markdown: \`$STATUS_MD\`
EOF

echo
echo "[+] SOCMINT v12.10.14 fresh DB release gate PASSED"
echo "[+] Status JSON: $STATUS_JSON"
echo "[+] Status Markdown: $STATUS_MD"
