#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

ADMIN_USER="${SOCMINT_TEST_ADMIN_USER:-$(grep '^SOCMINT_ADMIN_USER=' .env | cut -d= -f2-)}"
ADMIN_PASS="${SOCMINT_TEST_ADMIN_PASSWORD:-$(grep '^SOCMINT_ADMIN_PASSWORD=' .env | cut -d= -f2-)}"

./scripts/clean_v11_smoke_data.sh

docker compose exec -T \
  -e ADMIN_USER="$ADMIN_USER" \
  -e ADMIN_PASS="$ADMIN_PASS" \
  app python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar
from datetime import UTC, datetime

from src.socmint import database as db
from src.socmint.command_center import command_center_payload
from src.socmint.test_data_controls import clean_test_data, test_data_summary


def fail(message: str) -> None:
    raise SystemExit(f"FAIL v11.4 command center test-data controls: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def login_opener():
    base = "http://127.0.0.1:5000"
    user = os.environ["ADMIN_USER"]
    password = os.environ["ADMIN_PASS"]
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPRedirectHandler(),
    )
    login_html = opener.open(base + "/login", timeout=5).read().decode(errors="ignore")
    m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', login_html)
    if not m:
        m = re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']csrf_token["\']', login_html)
    require(bool(m), "csrf token not found")
    csrf = m.group(1)
    data = urllib.parse.urlencode({"username": user, "password": password, "csrf_token": csrf}).encode()
    opener.open(
        urllib.request.Request(base + "/login", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"),
        timeout=5,
    ).read()
    return base, opener


db.ensure_configured()

print("[+] Verify clean baseline")
clean_test_data(actor="v11.4-smoke-preclean")
summary = test_data_summary()
require(summary["status"] == "clean", f"expected clean baseline, got {summary['status']}")

print("[+] Create v11-smoke subject for UI/API controls")
stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
label = f"v11-smoke-command-center-{stamp}"
seed_value = f"v11-smoke-ui.{stamp}"
subject_id = db.create_spine_subject(label=label)
seed_id = db.add_spine_seed(
    subject_id=subject_id,
    seed_type="username",
    raw_value=seed_value,
    normalized_value=seed_value,
    pii_hash=hashlib.sha256(seed_value.encode()).hexdigest(),
)
require(subject_id > 0 and seed_id > 0, "failed to create smoke subject/seed")

summary = test_data_summary()
counts = summary.get("counts") or {}
require(summary["status"] == "needs_cleanup", "summary did not detect smoke data")
require(counts.get("subjects", 0) >= 1, "summary subject count did not increase")
require(summary.get("cleanup_available") is True, "cleanup_available should be true")
require(any(item.get("id") == subject_id for item in summary.get("subjects", [])), "summary missing created subject")

print("[+] Verify Command Center payload exposes test-data state")
payload = command_center_payload()
require(payload.get("schema") in {"socmint.command_center.v11_4", "socmint.command_center.v11_5", "socmint.command_center.v11_6"}, "command center schema not v11_4/v11_5/v11_6")
require("test_data" in payload, "command center payload missing test_data")
require((payload.get("summary") or {}).get("test_subject_count", 0) >= 1, "summary missing test_subject_count")
subject_rows = payload.get("subjects") or []
match = [item for item in subject_rows if item.get("id") == subject_id]
require(match, "command center subjects missing smoke subject")
require(match[0].get("is_test_data") is True, "smoke subject missing is_test_data badge")

print("[+] Verify authenticated JSON and browser surfaces")
base, opener = login_opener()
api = opener.open(base + "/api/v1/admin/test-data/summary", timeout=5)
require(api.status == 200, "test-data summary API did not return 200")
api_data = json.loads(api.read().decode())
require(api_data.get("schema") == "socmint.test_data_controls.v11_4", "summary API schema mismatch")
require((api_data.get("counts") or {}).get("subjects", 0) >= 1, "summary API missing smoke subject")

html_response = opener.open(base + "/command-center", timeout=5)
require(html_response.status == 200, "command center page did not return 200")
html = html_response.read().decode(errors="ignore")
require("Test Data Hygiene" in html, "command center missing Test Data Hygiene panel")
require("/api/v1/admin/test-data/summary" in html, "command center missing summary JSON link")
require("/command-center/test-data/clean" in html, "command center missing clean action")
require(label in html, "command center page missing smoke subject label")
require("test data" in html.lower(), "command center page missing test-data badge text")

print("[+] Verify cleanup control")
clean_result = clean_test_data(actor="v11.4-smoke-clean")
require(clean_result.get("subjects_deleted", 0) >= 1, "cleanup did not delete smoke subject")
post = test_data_summary()
require(post["status"] == "clean", f"post-clean status not clean: {post['status']}")

print(json.dumps({
    "schema": "socmint.v11_4.command_center_test_data_controls_smoke",
    "status": "pass",
    "subject_id": subject_id,
    "summary_before_clean": summary,
    "cleanup_result": clean_result,
}, indent=2, sort_keys=True))
print("PASS command center test data controls smoke v11.4")
PY
