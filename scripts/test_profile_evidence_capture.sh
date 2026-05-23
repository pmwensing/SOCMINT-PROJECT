#!/usr/bin/env bash
set -euo pipefail

echo "[+] Profile evidence capture smoke"
PYTHONPATH=src SOCMINT_ARTIFACT_DIR="${SOCMINT_ARTIFACT_DIR:-/tmp/socmint-v12-10-5-artifacts}" python3 - <<'PY'
import json
import os
import tempfile
from pathlib import Path

os.environ["SOCMINT_ARTIFACT_DIR"] = tempfile.mkdtemp(prefix="socmint-v12-10-5-")

from src.socmint.profile_evidence_capture_v12_10_5 import (
    SCHEMA,
    enhanced_username_from_url,
    enrich_profile_payload_with_evidence,
    is_asset_only_url,
)

assert enhanced_username_from_url("https://example.com/people/samantha4432") == "samantha4432"
assert enhanced_username_from_url("https://example.com/perfil/samantha4432") == "samantha4432"
assert enhanced_username_from_url("https://example.com/accounts/samantha4432") == "samantha4432"
assert enhanced_username_from_url("https://example.com/add/samantha4432") == "samantha4432"
assert is_asset_only_url("https://avatars.githubusercontent.com/u/123456.png") is True

payload = {
    "schema": "socmint.profile_fingerprint.v12_10_3",
    "candidate_count": 2,
    "needs_review_count": 2,
    "dossier_ready_count": 0,
    "candidates": [
        {
            "candidate_id": "cand-good",
            "context": {"linked_urls": ["https://example.org"], "banner_url": "https://example.com/banner.jpg"},
            "profile_fingerprint": {
                "platform": "github.com",
                "username": "",
                "profile_url": "https://github.com/people/samantha4432",
                "display_name": "Samantha",
                "bio_text": "maker profile",
                "location": "Canada",
                "linked_urls": [],
                "avatar_url": "https://example.com/avatar.png",
            },
        },
        {
            "candidate_id": "cand-asset",
            "context": {},
            "profile_fingerprint": {
                "platform": "githubusercontent",
                "username": "",
                "profile_url": "https://avatars.githubusercontent.com/u/123456.png",
                "linked_urls": [],
            },
        },
    ],
}

updated = enrich_profile_payload_with_evidence(payload, subject_id=3, live_capture_enabled=False)
cap = updated["evidence_capture"]
print(json.dumps(cap, indent=2))
assert cap["schema"] == SCHEMA
assert cap["captured_candidate_count"] == 2
assert cap["asset_only_candidate_count"] == 1
assert cap["text_fingerprint_ready_count"] >= 1
assert cap["visual_fingerprint_ready_count"] == 2

first = updated["candidates"][0]
fp = first["profile_fingerprint"]
assert fp["username"] == "samantha4432"
assert fp["html_sha256"]
assert fp["screenshot_sha256"]
assert fp["metadata_sha256"]
assert fp["text_fingerprint_hash"]
assert fp["visual_fingerprint_hash"]
assert first["evidence_capture"]["mode"] == "metadata_snapshot"

for file_info in first["evidence_capture"]["files"].values():
    assert Path(file_info["path"]).exists(), file_info
    assert file_info["sha256"]
    assert file_info["size_bytes"] > 0

print("PASS profile evidence capture smoke")
PY
