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

echo "[+] v7.5.2 compile"
python3 -m compileall -q src/socmint

echo "[+] v7.5.2 route check"
python3 - <<'PY'
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases

app = create_app()
register_full_report_aliases(app)
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if "dossier-v2" in rule.rule or "full-report" in rule.rule:
        print(rule.rule, sorted(rule.methods - {"HEAD", "OPTIONS"}))
PY

echo "[+] v7.5.2 UI/template check"
python3 - <<'PY'
from pathlib import Path

template = Path("src/socmint/templates/entity_dossier_v2.html").read_text()
for text in [
    "Run Full Report",
    "Latest Full Report Export",
    "Download Manifest",
    "Download ZIP",
    "latest_full_report_export",
]:
    assert text in template, text
print("UI controls present")
PY

echo "[+] v7.5.2 tests"
pytest -q tests/test_entity_dossier_v7_5.py
