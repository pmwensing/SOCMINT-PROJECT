
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
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if "evidence/links" in rule.rule or "evidence/attachment-map" in rule.rule:
        print(rule.rule, sorted(rule.methods - {"HEAD", "OPTIONS"}))
PY

echo "[+] Tests"
pytest -q tests/test_evidence_links_v7_4_1.py
