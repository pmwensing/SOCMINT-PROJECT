#!/usr/bin/env bash
set -euo pipefail

echo "[+] Identity link hypothesis smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.entity_alias_graph_v12_10_6 import build_entity_alias_graph
from src.socmint.identity_link_hypothesis_v12_10_7 import build_identity_link_hypotheses, export_identity_link_hypothesis_report

payload = {
    "subject": {"id": 7, "label": "Subject"},
    "seeds": [
        {"id": 1, "type": "email", "value": "sam@example.com"},
        {"id": 2, "type": "username", "value": "sam.case"},
    ],
    "observations": [
        {"id": 10, "type": "profile_url", "value": "https://example.com/sam.case", "confidence": 0.74, "source_ref": "connector:maigret", "evidence_ref": "ev-profile"},
        {"id": 11, "type": "email", "value": "sam@example.com", "confidence": 0.91, "source_ref": "connector:h8mail", "evidence_ref": "ev-email"},
    ],
}
profile_payload = {
    "candidates": [
        {
            "candidate_id": "cand-go",
            "identity_score": 0.88,
            "collision_status": "likely_same_online_identity",
            "evidence_refs": ["ev-profile"],
            "source_connector": "maigret",
            "analyst_review": {"review_state": "accepted"},
            "dossier_assertion_gate": {"dossier_ready": True},
            "evidence_capture": {"capture_id": "cap-1"},
            "profile_fingerprint": {
                "username": "sam.case",
                "platform": "example.com",
                "profile_url": "https://example.com/sam.case",
                "html_sha256": "h" * 64,
                "metadata_sha256": "m" * 64,
                "text_fingerprint_hash": "text1",
                "source_connectors": ["maigret"],
            },
        },
        {
            "candidate_id": "cand-hold",
            "identity_score": 0.4,
            "evidence_refs": ["ev-hold"],
            "analyst_review": {"review_state": "needs_more_evidence"},
            "dossier_assertion_gate": {"dossier_ready": False},
            "profile_fingerprint": {
                "username": "sam.hold",
                "platform": "example.net",
                "profile_url": "https://example.net/sam.hold",
                "source_connectors": ["sherlock"],
            },
        },
        {
            "candidate_id": "cand-fail",
            "identity_score": 0.03,
            "evidence_refs": ["ev-asset"],
            "analyst_review": {"review_state": "rejected"},
            "dossier_assertion_gate": {"suppressed": True, "dossier_ready": False},
            "profile_fingerprint": {
                "username": "asset",
                "platform": "cdn.example",
                "profile_url": "https://cdn.example/avatar.png",
                "asset_only_url": True,
                "source_connectors": ["social-analyzer"],
            },
        },
    ]
}

alias_graph = build_entity_alias_graph(payload, profile_payload)
links = build_identity_link_hypotheses(alias_graph, profile_payload)
print(links["schema"])
print(links["go_count"], links["hold_count"], links["fail_count"])
assert links["schema"] == "socmint.identity_link_hypothesis.v12_10_7"
assert links["hypothesis_count"] == 3
assert links["go_count"] == 1
assert links["hold_count"] >= 1
assert links["fail_count"] == 1
go = next(row for row in links["hypotheses"] if row["candidate_id"] == "cand-go")
assert go["decision"] == "GO"
assert go["dossier_assertion_ready"] is True
assert go["strong_alias_count"] >= 1
hold = next(row for row in links["hypotheses"] if row["candidate_id"] == "cand-hold")
assert hold["decision"] == "HOLD"
assert any("analyst review" in reason for reason in hold["reasons"])

mime, name, body = export_identity_link_hypothesis_report(links, "md")
assert mime == "text/markdown"
assert name == "identity-link-hypotheses.md"
assert "Identity Link Hypotheses" in body
assert "GO: 1" in body
print("PASS identity link hypothesis smoke")
PY
