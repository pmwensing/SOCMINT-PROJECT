#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(pwd)}"
APP_SERVICE="${APP_SERVICE:-app}"
OUT_DIR="${OUT_DIR:-support_bundle_v13_34}"

cd "$ROOT_DIR"
mkdir -p "$OUT_DIR"

echo "[+] SOCMINT v13.34 support bundle capture"
echo "[+] root=$ROOT_DIR out=$OUT_DIR"

{
  echo "# SOCMINT Support Bundle v13.34"
  echo "Generated: $(date -u --iso-8601=seconds 2>/dev/null || date -u)"
  echo
  echo "## Git"
  git rev-parse --show-toplevel 2>/dev/null || true
  git rev-parse HEAD 2>/dev/null || true
  git status --short 2>/dev/null || true
  echo
  echo "## Docker Compose"
  docker compose ps 2>/dev/null || true
} > "$OUT_DIR/summary.txt"

echo "[+] Capture app diagnostics through Flask app"
docker compose exec -T "$APP_SERVICE" python - <<'PY' > "$OUT_DIR/support_bundle_api.json"
import json
from src.socmint.wsgi import app
from src.socmint.support_bundle_v13_34 import support_bundle_payload
print(json.dumps(support_bundle_payload(app=app), indent=2, sort_keys=True))
PY

echo "[+] Capture recent app logs"
docker compose logs --tail=500 "$APP_SERVICE" > "$OUT_DIR/app_logs_tail.txt" 2>&1 || true

echo "[+] Create archive"
zip -r "${OUT_DIR}.zip" "$OUT_DIR" >/dev/null
ls -lh "${OUT_DIR}.zip"

echo "[+] Support bundle complete: ${OUT_DIR}.zip"
