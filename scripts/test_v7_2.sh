#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

if [ -f .env ]; then
  set +u
  set -a
  . ./.env
  set +a
  set -u
fi

echo "[+] Compile"
python3 -m compileall -q src/socmint

echo "[+] Route check"
python3 - <<'PY'
from socmint.dashboard import create_app

app = create_app()
found = []
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if "reports/review" in rule.rule or "reports/runs" in rule.rule:
        found.append(rule.rule)
        print(rule.rule, sorted(rule.methods - {"HEAD", "OPTIONS"}))

required = {
    "/reports/review",
    "/api/v1/reports/review/summary",
    "/api/v1/reports/review/items",
    "/api/v1/reports/runs",
}
missing = required - set(found)
if missing:
    raise SystemExit("missing v7.2 routes: " + ", ".join(sorted(missing)))
PY

echo "[+] v7.2 tests"
pytest -q tests/test_report_review_v7_2.py
