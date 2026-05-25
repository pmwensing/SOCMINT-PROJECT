#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-$PWD}"

python -m py_compile scripts/build_approved_migration_draft_v12_10_35.py
python -m pytest -q tests/test_v12_10_35_approved_migration_draft.py

# This may refuse if approval_valid is false. That is acceptable only if refusal file exists.
set +e
python scripts/build_approved_migration_draft_v12_10_35.py
STATUS=$?
set -e

if [ "$STATUS" != "0" ]; then
  test -f release/approved_migration_draft/APPROVED_MIGRATION_DRAFT_REFUSAL_V12_10_35.md
  echo "[!] v12.10.35 refused draft because approval is invalid or incomplete"
  echo "[!] Fix release/human_review_gate/approval_list.json, run make approve121034, then rerun make test121035"
  exit 0
fi

test -f release/approved_migration_draft/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py
test -f release/approved_migration_draft/APPROVED_MIGRATION_DRAFT_MANIFEST_V12_10_35.json
test ! -f alembic/versions/0018_APPROVED_MODEL_MIGRATION_DRAFT_V12_10_35.py

echo "[+] v12.10.35 approved migration draft builder passed"
