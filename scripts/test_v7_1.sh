#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"

echo "[+] Compile package"
python3 -m compileall -q src/socmint

echo "[+] Route check"
python3 - <<'PY'
from socmint.dashboard import create_app

app = create_app()
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if "drift-report" in rule.rule or "audit-report" in rule.rule or "full-report" in rule.rule:
        print(rule.rule, sorted(rule.methods - {"HEAD", "OPTIONS"}))
PY

echo "[+] v7.1 tests"
if [ -f tests/test_v7_1_drift_audit_full_report.py ]; then
  pytest -q tests/test_v7_1_drift_audit_full_report.py
else
  pytest -q
fi
