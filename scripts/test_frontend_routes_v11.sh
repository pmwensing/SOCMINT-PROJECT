#!/usr/bin/env bash
set -euo pipefail

ROOT="${SOCMINT_ROOT:-$(pwd)}"
cd "$ROOT"

ADMIN_USER="${SOCMINT_TEST_ADMIN_USER:-$(grep '^SOCMINT_ADMIN_USER=' .env | cut -d= -f2-)}"
ADMIN_PASS="${SOCMINT_TEST_ADMIN_PASSWORD:-$(grep '^SOCMINT_ADMIN_PASSWORD=' .env | cut -d= -f2-)}"

docker compose exec -T \
  -e ADMIN_USER="$ADMIN_USER" \
  -e ADMIN_PASS="$ADMIN_PASS" \
  app python - <<'PY'
import os
import re
import json
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar
from html.parser import HTMLParser
from src.socmint.wsgi import app

base = "http://127.0.0.1:5000"
user = os.environ["ADMIN_USER"]
password = os.environ["ADMIN_PASS"]

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cj),
    urllib.request.HTTPRedirectHandler(),
)

login_html = opener.open(base + "/login", timeout=5).read().decode(errors="ignore")
m = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', login_html)
if not m:
    m = re.search(r'value=["\']([^"\']+)["\'][^>]*name=["\']csrf_token["\']', login_html)
if not m:
    raise SystemExit("FAIL csrf token not found")
csrf = m.group(1)

data = urllib.parse.urlencode({
    "username": user,
    "password": password,
    "csrf_token": csrf,
}).encode()

opener.open(
    urllib.request.Request(
        base + "/login",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    ),
    timeout=5,
).read()

seed_paths = [
    "/",
    "/command-center",
    "/login",
    "/jobs",
    "/cases",
    "/spine",
    "/workbench/jobs",
    "/dossier/certification-dashboard",
    "/product/operator-runbook",
    "/api/v1/command-center",
    "/api/v1/jobs/health",
    "/api/v1/tor/status",
]

for rule in app.url_map.iter_rules():
    rule_s = str(rule)
    if "<" in rule_s:
        continue
    if "GET" not in rule.methods:
        continue
    if rule_s.startswith("/static"):
        continue
    if rule_s not in seed_paths and any(x in rule_s for x in [
        "admin", "product", "dossier", "report", "export", "evidence",
        "spine", "cases", "jobs", "workbench", "command"
    ]):
        seed_paths.append(rule_s)

seen = set()
results = []
all_links = {}

source_hits = []
for template_path in [
    "src/socmint/templates/base.html",
    "src/socmint/templates/command_center.html",
]:
    try:
        text = open(template_path, "r", encoding="utf-8").read()
    except FileNotFoundError:
        continue
    if "/spine/subjects/1/dossier" in text:
        source_hits.append(template_path)


for path in seed_paths:
    if path in seen:
        continue
    seen.add(path)
    try:
        r = opener.open(base + path, timeout=8)
        status = r.status
        ctype = r.headers.get("Content-Type", "")
        body = r.read(250000).decode(errors="ignore")
        parser = LinkParser()
        if "html" in ctype.lower() or body.lstrip().startswith("<!DOCTYPE html"):
            parser.feed(body)
        links = parser.links
        all_links[path] = links
        issues = []
        if status >= 400:
            issues.append("bad_status")
        # v11.2 functional smoke creates real subjects. Once subject id 1 exists,
        # rendered pages may legitimately include /spine/subjects/1/dossier.
        # The original bug was a hard-coded literal in active templates, so enforce
        # that separately with a source scan below instead of flagging dynamic HTML.
        if "Run the CLI" in body:
            issues.append("legacy_cli_copy")
        if path in {"/", "/command-center"} and "/api/v1/command-center" in links:
            issues.append("api_command_center_link_in_browser_nav")
        if path == "/" and "/command-center" not in links:
            issues.append("missing_browser_command_center_link")
        results.append({
            "path": path,
            "status": status,
            "content_type": ctype,
            "links": len(links),
            "issue": "; ".join(issues),
        })
    except urllib.error.HTTPError as e:
        results.append({"path": path, "status": e.code, "issue": "http_error"})
    except Exception as e:
        results.append({"path": path, "status": "ERR", "issue": repr(e)})

print("=== FRONTEND ROUTE AUDIT v11.1.1 ===")
failed = False
for row in results:
    ok = not row.get("issue") and row["status"] in (200, 302)
    marker = "OK" if ok else "CHECK"
    print(f"{marker:5} {str(row['status']):>4} {row['path']} {row.get('issue','')}")
    if not ok:
        failed = True

print()
print("=== GLOBAL NAV LINKS FROM / ===")
for link in all_links.get("/", []):
    print(link)

if source_hits:
    print()
    print("=== SOURCE TEMPLATE HARD-CODE FINDINGS ===")
    for path in source_hits:
        print(path)
    failed = True

if failed:
    print()
    print("=== HIGH PRIORITY FINDINGS ===")
    for row in results:
        if row.get("issue") or row["status"] not in (200, 302):
            print(json.dumps(row, indent=2))
    raise SystemExit(1)

print()
print("PASS frontend route audit v11.1.1")
PY
