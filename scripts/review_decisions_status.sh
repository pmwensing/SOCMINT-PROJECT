#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

if [ -f .env ]; then
  set +u
  set -a
  . ./.env
  set +a
  set -u
fi

python3 - <<'PY'
from socmint.report_review import review_decision_table_available
from socmint.report_review import review_summary

print("review_decisions table available:", review_decision_table_available())
print("summary:", review_summary())
PY
