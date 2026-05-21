#!/usr/bin/env bash
set -euo pipefail

echo "[+] Profile evidence capture quality smoke"
PYTHONPATH=src SOCMINT_ARTIFACT_DIR="${SOCMINT_ARTIFACT_DIR:-/tmp/socmint-v12-10-5-1-artifacts}" python3 - <<'PY'
import os
import tempfile

os.environ["SOCMINT_ARTIFACT_DIR"] = tempfile.mkdtemp(prefix="socmint-v12-10-5-1-")

from src.socmint.profile_evidence_capture_v12_10_5 import (
    canonical_profile_username,
    enhanced_username_from_url,
    enrich_profile_payload_with_evidence,
    is_asset_only_url,
)

# Route placeholder username rewrites.
assert canonical_profile_username("people", "https://redbubble.com/people/samantha4432") == "samantha4432"
assert canonical_profile_username("perfil", "https://mercadolivre.com.br/perfil/samantha4432") == "samantha4432"
assert canonical_profile_username("accounts", "https://www.kongregate.com/accounts/samantha4432") == "samantha4432"
assert canonical_profile_username("add", "https://www.snapchat.com/add/samantha4432") == "samantha4432"

# Query parameter username extraction.
assert enhanced_username_from_url("https://www.roblox.com/user.aspx?username=samantha4432") == "samantha4432"
assert enhanced_username_from_url("https://example.com/profile?user=samantha4432") == "samantha4432"
assert enhanced_username_from_url("https://example.com/p?handle=samantha4432") == "samantha4432"

# Expanded asset/CDN detection.
asset_urls = [
    "https://tr.rbxcdn.com/30DAY-Avatar-260729AE68D05D5100DE836CA3D0E606-Png/352/352/Avatar/Png/noFilter",
    "https://simg-ssl.duolingo.com/ssr-avatars/1294536029/SSR-ViAk9LCjhm",
    "https://yt3.googleusercontent.com/ytc/AIdro_lrC-XjiWgV1N7d4=s900-c-k-c0x00ffffff-no-rj",
    "https://p16-common-sign.tiktokcdn.com/tos-alisg-avt-0068/example.jpeg",
    "https://s.pinimg.com/webapp/logo_transparent_144x144-3da7a67b.png",
    "https://assets.tumblr.com/images/default_avatar/cone_closed_512.png",
    "https://web.static.mmcdn.com/favicons/mstile-144x144.png?hash=a83d70c6fcc9",
]
for url in asset_urls:
    assert is_asset_only_url(url) is True, url

payload = {
    "schema": "socmint.profile_fingerprint.v12_10_3",
    "candidate_count": 3,
    "needs_review_count": 3,
    "dossier_ready_count": 0,
    "candidates": [
        {
            "candidate_id": "route-redbubble",
            "identity_score": 0.3,
            "collision_status": "likely_username_collision",
            "negative_reasons": [],
            "identity_link_hypothesis": {"can_promote_to_dossier_assertion": False},
            "dossier_assertion_gate": {"dossier_ready": False},
            "context": {},
            "profile_fingerprint": {"platform": "redbubble.com", "username": "people", "profile_url": "https://redbubble.com/people/samantha4432", "linked_urls": []},
        },
        {
            "candidate_id": "query-roblox",
            "identity_score": 0.3,
            "collision_status": "likely_username_collision",
            "negative_reasons": [],
            "identity_link_hypothesis": {"can_promote_to_dossier_assertion": False},
            "dossier_assertion_gate": {"dossier_ready": False},
            "context": {},
            "profile_fingerprint": {"platform": "roblox.com", "username": "user.aspx", "profile_url": "https://www.roblox.com/user.aspx?username=samantha4432", "linked_urls": []},
        },
        {
            "candidate_id": "asset-rbxcdn",
            "identity_score": 0.78,
            "collision_status": "weak_username_collision",
            "negative_reasons": [],
            "identity_link_hypothesis": {"can_promote_to_dossier_assertion": True, "relationship": "candidate_profile_likely_same_online_identity_cluster"},
            "dossier_assertion_gate": {"dossier_ready": True, "assertion_type": "same_online_identity_cluster"},
            "context": {},
            "profile_fingerprint": {"platform": "tr.rbxcdn.com", "username": "30DAY-Avatar", "profile_url": asset_urls[0], "linked_urls": []},
        },
    ],
}
updated = enrich_profile_payload_with_evidence(payload, subject_id=3, live_capture_enabled=False)
cap = updated["evidence_capture"]
assert cap["rewritten_username_count"] >= 2
assert cap["asset_only_candidate_count"] == 1
assert cap["suppressed_asset_only_assertion_count"] == 1

by_id = {c["candidate_id"]: c for c in updated["candidates"]}
assert by_id["route-redbubble"]["profile_fingerprint"]["username"] == "samantha4432"
assert by_id["query-roblox"]["profile_fingerprint"]["username"] == "samantha4432"
asset = by_id["asset-rbxcdn"]
assert asset["profile_fingerprint"]["asset_only_url"] is True
assert asset["collision_status"] == "asset_only_not_profile"
assert asset["identity_link_hypothesis"]["can_promote_to_dossier_assertion"] is False
assert asset["dossier_assertion_gate"]["assertion_type"] == "asset_only_profile_suppressed"
assert asset["dossier_assertion_gate"]["suppressed"] is True

print("PASS profile evidence capture quality smoke")
PY
