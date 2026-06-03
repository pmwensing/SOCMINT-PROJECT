#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(pwd)}"
SUBJECT_ID="${SUBJECT_ID:-4}"
APP_SERVICE="${APP_SERVICE:-app}"

cd "$ROOT_DIR"

echo "[+] v13.33 Final RC runtime acceptance"
echo "[+] root=$ROOT_DIR subject=$SUBJECT_ID"

echo "[+] Docker health"
docker compose ps
for i in {1..60}; do
  cid="$(docker compose ps -q "$APP_SERVICE" 2>/dev/null || true)"
  status="unknown"
  if [ -n "$cid" ]; then
    status="$(docker inspect -f '{{.State.Health.Status}}' "$cid" 2>/dev/null || true)"
  fi
  echo "app health: ${status:-unknown}"
  [ "$status" = "healthy" ] && break
  sleep 2
done

echo "[+] Route acceptance with forced session"
docker compose exec -T "$APP_SERVICE" python - <<'PY'
from src.socmint.wsgi import app

subject_id = 4
client = app.test_client()
with client.session_transaction() as sess:
    sess["user"] = "admin"
    sess["is_admin"] = True
    sess["role"] = "admin"

paths = [
    "/command-center",
    "/review/normalization-queue",
    f"/subjects/{subject_id}/dossier/readiness",
    f"/subjects/{subject_id}/claim-evidence-ledger",
    f"/spine/subjects/{subject_id}/dossier",
    f"/spine/subjects/{subject_id}/full-report/history",
    f"/spine/subjects/{subject_id}/full-report/view",
    f"/spine/subjects/{subject_id}/full-report/retention",
    "/release/final-rc/v13.33",
    "/api/v1/release/final-rc/v13.33",
]

failed = False
for path in paths:
    resp = client.get(path)
    print(path, resp.status_code)
    if resp.status_code >= 500:
        failed = True
        print(resp.get_data(as_text=True)[:2000])

if failed:
    raise SystemExit(1)
PY

echo "[+] Export acceptance"
docker compose exec -T "$APP_SERVICE" python - <<'PY'
from pathlib import Path
from src.socmint.entity_dossier_v2 import dossier_root, export_full_entity_dossier_v2
from src.socmint.full_report_alias import latest_full_report_export
from src.socmint.full_report_history import full_report_export_history
from src.socmint.final_rc_routes_v13_33 import final_rc_status_payload

subject_id = 4
root = dossier_root()
probe = root / ".v13_33_write_test"
probe.write_text("ok")
probe.unlink()
print("dossier_root:", root)

result = export_full_entity_dossier_v2(subject_id)
required_paths = ["zip_path", "manifest_path", "html_path", "markdown_path", "json_path"]
for key in required_paths:
    path = Path(result[key])
    print(key, path.name, path.exists(), path.stat().st_size if path.exists() else 0)
    if not path.exists() or path.stat().st_size <= 0:
        raise SystemExit(f"bad artifact: {key} -> {path}")

latest = latest_full_report_export(subject_id)
history = full_report_export_history(subject_id)
rc = final_rc_status_payload()
print("latest available:", latest.get("available"))
print("history count:", history.get("count"))
print("rc status:", rc.get("status"))
for key in ["zip_name", "manifest_name", "html_name", "markdown_name", "json_name"]:
    print(key, latest.get(key))
    if not latest.get(key):
        raise SystemExit(f"missing latest artifact: {key}")
if rc.get("version") != "v13.33" or rc.get("status") != "release_candidate_locked":
    raise SystemExit("bad final RC status payload")
PY

echo "[+] Check app logs for server errors"
docker compose logs --tail=500 "$APP_SERVICE" | grep -A120 -B30 -E 'Traceback|Exception on|ERROR|status_code":500' && exit 1 || true

echo "[+] v13.33 Final RC runtime acceptance complete"
