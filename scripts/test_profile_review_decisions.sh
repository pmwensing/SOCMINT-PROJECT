#!/usr/bin/env bash
set -euo pipefail

echo "[+] Candidate profile review decisions smoke"
PYTHONPATH=src SOCMINT_ARTIFACT_DIR="${SOCMINT_ARTIFACT_DIR:-/tmp/socmint-v12-10-4-artifacts}" python3 - <<'PY'
import json
import os
import tempfile

from src.socmint import database as db
from src.socmint.candidate_profile_review_v12_10_4 import (
    apply_profile_review_decisions,
    export_profile_review_report,
    review_candidate_profile,
)
from src.socmint.profile_fingerprint_v12_10_3 import build_profile_fingerprint_payload

os.environ["SOCMINT_ARTIFACT_DIR"] = tempfile.mkdtemp(prefix="socmint-v12-10-4-")
db.configure_database("sqlite:///:memory:")
subject_id = db.create_spine_subject("Decision Smoke")

payload = {
    "subject": {"id": subject_id},
    "seeds": [
        {"id": 1, "type": "email", "value": "samantha4432@hotmail.com"},
        {"id": 2, "type": "username", "value": "samantha4432"},
    ],
    "observations": [
        {
            "id": 100,
            "subject_id": subject_id,
            "run_id": 55,
            "type": "profile_url",
            "value": "https://github.com/samantha4432",
            "connector": "social-analyzer",
            "source_ref": "run:55:social-analyzer",
            "evidence_ref": "sha256:abc",
            "payload": {"context": {"platform": "GitHub", "display_name": "Samantha", "bio": "maker profile"}},
        },
        {
            "id": 101,
            "subject_id": subject_id,
            "run_id": 56,
            "type": "account_presence",
            "value": "RandomForum",
            "connector": "holehe",
            "source_ref": "run:56:holehe",
            "evidence_ref": "sha256:def",
            "payload": {"context": {"target": "samantha4432@hotmail.com"}},
        },
    ],
    "assertions": [],
}

profile_payload = build_profile_fingerprint_payload(payload)
assert profile_payload["candidate_count"] >= 2
candidate_id = profile_payload["candidates"][0]["candidate_id"]

result = review_candidate_profile(subject_id, candidate_id, "accept_same_entity", profile_payload, actor="tester", note="accepted for smoke")
print(json.dumps(result, indent=2))
assert result["review_state"] == "accepted"
assert result["assertion_id"]

updated = apply_profile_review_decisions(profile_payload, subject_id)
accepted = [c for c in updated["candidates"] if c["candidate_id"] == candidate_id][0]
assert accepted["analyst_review"]["review_state"] == "accepted"
assert accepted["dossier_ready"] is True
assert updated["review_decision_counts"]["accepted"] == 1
assert updated["dossier_ready_count"] == 1

other = [c for c in updated["candidates"] if c["candidate_id"] != candidate_id][0]
reject = review_candidate_profile(subject_id, other["candidate_id"], "reject_collision", updated, actor="tester", note="collision for smoke")
assert reject["review_state"] == "rejected"
updated2 = apply_profile_review_decisions(updated, subject_id)
assert updated2["review_decision_counts"]["rejected"] == 1
assert updated2["needs_review_count"] >= 0

mime_json, filename_json, body_json = export_profile_review_report(subject_id, updated2, fmt="json")
assert mime_json == "application/json"
assert filename_json.endswith(".json")
assert "review_decision_counts" in json.loads(body_json)

mime_md, filename_md, body_md = export_profile_review_report(subject_id, updated2, fmt="md")
assert mime_md == "text/markdown"
assert filename_md.endswith(".md")
assert "Candidate Profile Review Report" in body_md

print("PASS profile review decisions smoke")
PY
