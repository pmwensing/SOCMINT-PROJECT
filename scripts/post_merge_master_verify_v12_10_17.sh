#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

REPORT_ROOT="var/socmint/rc_reports"
WORK_ROOT="var/test_v12_10_17_post_merge"
DB_PATH="$WORK_ROOT/socmint_v12_10_17_post_merge.db"
DATA_DIR="$WORK_ROOT/data"
STATUS_JSON="$REPORT_ROOT/socmint_v12_10_17_post_merge_master_verify_status.json"
STATUS_MD="$REPORT_ROOT/socmint_v12_10_17_post_merge_master_verify_status.md"
CI_MODE="${SOCMINT_CI_MODE:-false}"
mkdir -p "$REPORT_ROOT" "$WORK_ROOT" "$DATA_DIR"

export PYTHONPATH="$ROOT/src:$ROOT"
export DATABASE_URL="sqlite:///$DB_PATH"
export SOCMINT_DATA_DIR="$DATA_DIR"
export SOCMINT_LOG_FILE="$WORK_ROOT/socmint.log"
export SOCMINT_SECRET_KEY="test-v12-10-17-secret-key-000000000000000000000000"
export SOCMINT_AUTO_CREATE_DB=true
export SOCMINT_ALLOW_SIGNUP=false
export SOCMINT_DOCKER_TOR=true

record_json() {
  local status="$1"
  local decision="$2"
  local message="$3"
  python3 - <<PY
import json
from datetime import UTC, datetime
payload = {
  "schema": "socmint.release.post_merge_master_verify.v12_10_17",
  "version": "12.10.17",
  "generated_at": datetime.now(UTC).isoformat(),
  "status": "$status",
  "decision": "$decision",
  "message": "$message",
  "ci_mode": "$CI_MODE".lower() == "true",
  "work_root": "$WORK_ROOT",
  "database_url": "$DATABASE_URL",
  "reports": {"status_json": "$STATUS_JSON", "status_markdown": "$STATUS_MD"}
}
open("$STATUS_JSON", "w").write(json.dumps(payload, indent=2, sort_keys=True))
PY
}

section() {
  echo
  echo "[+] $*"
  echo "## $*" >> "$STATUS_MD"
  echo >> "$STATUS_MD"
}

pass_line() {
  echo "PASS $*"
  echo "- PASS $*" >> "$STATUS_MD"
}

fail() {
  echo "FAIL $*" >&2
  echo "- FAIL $*" >> "$STATUS_MD"
  record_json "fail" "FAIL" "$*"
  exit 1
}

trap 'fail "post-merge verification aborted at line $LINENO"' ERR

: > "$STATUS_MD"
section "SOCMINT v12.10.17 Master Post-Merge Verification"

section "1. clean checkout or CI checkout"
if [ "$CI_MODE" = "true" ]; then
  pass_line "CI checkout accepted"
else
  git status --short
  if [ -n "$(git status --short)" ]; then
    fail "working tree is not clean"
  fi
  current_branch="$(git branch --show-current)"
  if [ "$current_branch" != "master" ]; then
    fail "expected master branch, got $current_branch"
  fi
  pass_line "clean master checkout"
fi

section "2. version and release manifest alignment"
python3 - <<'PY'
import json
import re
from pathlib import Path
manifest = json.loads(Path("release/CURRENT_STATUS.json").read_text())
pyproject = Path("pyproject.toml").read_text()
match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
assert match, "pyproject version missing"
from src.socmint.version import VERSION, RELEASE_TAG
assert VERSION == "12.10.17", VERSION
assert manifest["version"] == VERSION, (manifest["version"], VERSION)
assert match.group(1) == VERSION, (match.group(1), VERSION)
assert manifest["release_tag"] == RELEASE_TAG, (manifest["release_tag"], RELEASE_TAG)
print({"version": VERSION, "release_tag": RELEASE_TAG})
PY
pass_line "version metadata aligned"

section "3. empty database migration smoke"
rm -f "$DB_PATH"
SOCMINT_AUTO_CREATE_DB=false alembic upgrade head
python3 - <<'PY'
from sqlalchemy import create_engine, inspect
import os
engine = create_engine(os.environ["DATABASE_URL"])
tables = set(inspect(engine).get_table_names())
required = {"spine_subjects", "spine_seeds", "spine_connector_runs", "spine_observations", "spine_dossier_assertions", "spine_validation_events"}
missing = sorted(required - tables)
assert not missing, f"missing tables after alembic: {missing}"
print({"table_count": len(tables), "required_present": sorted(required)})
PY
export SOCMINT_AUTO_CREATE_DB=true
pass_line "empty DB migration passed"

section "4. runtime route release gate"
python3 scripts/runtime_route_release_gate_v12_10_17.py
pass_line "runtime route gate passed"

section "5. release status payload smoke"
python3 - <<'PY'
from src.socmint.release_status_v12_10_17 import latest_gate_reports, release_status
status = release_status()
latest = latest_gate_reports()
assert status["schema"] == "socmint.release_status.v12_10_17", status.get("schema")
assert latest["schema"] == "socmint.release_gates.latest.v12_10_17", latest.get("schema")
assert status["release"]["version"] == "12.10.17", status["release"]
print({"release_status": status["status"], "latest_gate_status": latest["status"]})
PY
pass_line "release status payloads generated"

section "6. latest gate report after verification"
python3 - <<'PY'
from src.socmint.release_status_v12_10_17 import latest_gate_reports
latest = latest_gate_reports()
assert latest.get("latest"), latest
print(latest["latest"])
PY
pass_line "latest gate report readable"

record_json "pass" "GO" "SOCMINT v12.10.17 post-merge verification passed"
cat >> "$STATUS_MD" <<EOF

## Result

- Status: \`pass\`
- Decision: \`GO\`
- JSON: \`$STATUS_JSON\`
- Markdown: \`$STATUS_MD\`
EOF

echo
echo "[+] SOCMINT v12.10.17 post-merge verification PASSED"
echo "[+] Status JSON: $STATUS_JSON"
echo "[+] Status Markdown: $STATUS_MD"
