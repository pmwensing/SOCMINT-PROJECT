#!/usr/bin/env bash
set -euo pipefail

SCRIPT_LOCATION="alembic"
if [ -f alembic.ini ]; then
  SCRIPT_LOCATION="$(python - <<'PY'
import configparser
cfg = configparser.ConfigParser()
cfg.read("alembic.ini")
print(cfg.get("alembic", "script_location", fallback="alembic"))
PY
)"
fi

VERSIONS_DIR="${SCRIPT_LOCATION}/versions"
mkdir -p "$VERSIONS_DIR"

DEST="${VERSIONS_DIR}/0017_v12_10_schema_reconciliation.py"
SRC="alembic/versions/0017_v12_10_schema_reconciliation.py"

if [ ! -f "$DEST" ] && [ -f "$SRC" ]; then
  cp "$SRC" "$DEST"
fi

CURRENT_HEAD="$(alembic heads 2>/dev/null | awk '{print $1}' | grep -v '^0017_v12_10_schema_reconciliation$' | tail -n 1 || true)"
CURRENT_HEAD="${CURRENT_HEAD:-0014_case_access}"

mkdir -p release
printf '%s\n' "$CURRENT_HEAD" > release/V12_10_30_ALEMBIC_BASE_HEAD.txt

python - <<PY
from pathlib import Path
import re

p = Path("$DEST")
s = p.read_text()

s = re.sub(
    r'revision\\s*=\\s*["\\'][^"\\']+["\\']',
    'revision = "0017_v12_10_schema_reconciliation"',
    s,
)

s = re.sub(
    r'down_revision\\s*=\\s*["\\'][^"\\']+["\\']',
    'down_revision = "$CURRENT_HEAD"',
    s,
)

if "def _drop_if_exists" not in s:
    s = s.replace(
        "def _create_if_missing(name, *cols):",
        '''def _drop_if_exists(name):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if name in inspector.get_table_names():
        op.drop_table(name)


def _create_if_missing(name, *cols):''',
    )

s = s.replace("        op.drop_table(table)", "        _drop_if_exists(table)")
p.write_text(s)
print("[+] patched 0017 down_revision -> $CURRENT_HEAD")
PY

if [ "$SRC" != "$DEST" ]; then
  cp "$DEST" "$SRC" 2>/dev/null || true
fi

alembic heads
HEADS="$(alembic heads | awk '{print $1}')"
echo "$HEADS" | grep -qx "0017_v12_10_schema_reconciliation"
test "$(echo "$HEADS" | wc -l | tr -d ' ')" = "1"

echo "[+] 0017 is sole Alembic head"
