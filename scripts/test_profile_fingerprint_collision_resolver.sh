#!/usr/bin/env bash
set -euo pipefail

echo "[+] Profile fingerprint collision resolver smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.profile_fingerprint_v12_10_3 import PIPELINE, build_profile_fingerprint_payload
import json

payload = {
    "subject": {"id": 3},
    "seeds": [
        {"id": 1, "type": "email", "value": "samantha4432@hotmail.com"},
        {"id": 2, "type": "username", "value": "samantha4432"},
    ],
    "observations": [
        {
            "id": 100,
            "subject_id": 3,
            "run_id": 55,
            "type": "profile_url",
            "value": "https://github.com/samantha4432",
            "connector": "social-analyzer",
            "source_ref": "run:55:social-analyzer",
            "evidence_ref": "sha256:abc",
            "payload": {"context": {"platform": "GitHub", "deep_enrichment": True, "display_name": "Samantha", "bio": "maker profile"}},
        },
        {
            "id": 101,
            "subject_id": 3,
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

result = build_profile_fingerprint_payload(payload)
print(json.dumps(result, indent=2))
assert result["schema"] == "socmint.profile_fingerprint.v12_10_3"
assert result["pipeline"] == PIPELINE
assert result["connector_finding_count"] == 2
assert result["candidate_count"] >= 2
assert any(c["profile_fingerprint"]["profile_url"] == "https://github.com/samantha4432" for c in result["candidates"])
assert all(c["pipeline_trace"] == PIPELINE for c in result["candidates"])
for candidate in result["candidates"]:
    assert candidate["stage"] == "candidate_profile"
    assert candidate["profile_fingerprint"]["stage"] == "profile_fingerprint"
    assert candidate["collision_resolution"]["stage"] == "collision_resolver"
    assert candidate["identity_link_hypothesis"]["stage"] == "identity_link_hypothesis"
    assert candidate["analyst_review"]["stage"] == "analyst_review"
    assert candidate["dossier_assertion_gate"]["stage"] == "dossier_assertion"
assert any(c["collision_status"] in {"weak_username_collision", "likely_username_collision"} for c in result["candidates"])
assert result["gate"]["status"] == "review"
print("PASS profile fingerprint collision resolver smoke")
PY
