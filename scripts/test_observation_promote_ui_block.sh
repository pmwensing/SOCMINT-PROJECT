#!/usr/bin/env bash
set -euo pipefail

echo "[+] Observation promote UI block smoke"
python3 - <<'PY'
from pathlib import Path
import re

template = Path("src/socmint/templates/spine_intelligence.html").read_text()

assert "blocked_observation_types" in template
assert '"static_asset_url"' in template
assert '"avatar_url"' in template
assert '"asset_artifact_url"' in template
assert '"metadata_artifact"' in template
assert '"platform_artifact_id"' in template

# v12.10.7.4 uses a safer promotion_gate fallback before checking .blocked.
assert "promotion_gate = observation.promotion_gate or {}" in template
assert "observation_blocked = observation.promotion_blocked or promotion_gate.blocked or observation.type in blocked_observation_types" in template

assert "Promotion blocked: not identity evidence" in template

section = re.search(
    r'<section class="panel">\s*<h2>Real Enrichment Observations</h2>.*?</section>',
    template,
    re.S,
)
assert section, "Real Enrichment Observations section not found"
section_text = section.group(0)

blocked_branch = re.search(r"{% if observation_blocked %}(.*?){% else %}", section_text, re.S)
assert blocked_branch, "blocked branch missing"
assert "Promote to confirmed assertion" not in blocked_branch.group(1), "blocked branch still renders promote button text"
assert "<form method=\"post\"" not in blocked_branch.group(1), "blocked branch still renders promote form"

allowed_branch = re.search(r"{% else %}(.*?){% endif %}", section_text, re.S)
assert allowed_branch, "allowed branch missing"
assert "Promote to confirmed assertion" in allowed_branch.group(1), "allowed branch no longer renders promote button"

print("PASS observation promote UI block smoke")
PY
