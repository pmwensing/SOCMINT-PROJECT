#!/usr/bin/env bash
set -euo pipefail

echo "[+] Dossier assertion review packet smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.dossier_assertion_projection_v12_10_8 import build_dossier_assertion_projection
from src.socmint.dossier_assertion_review_packet_v12_10_9 import build_dossier_assertion_review_packet, export_dossier_assertion_review_packet_report
from src.socmint.entity_alias_graph_v12_10_6 import build_entity_alias_graph
from src.socmint.identity_link_hypothesis_v12_10_7 import build_identity_link_hypotheses

payload = {
    "subject": {"id": 9, "label": "Subject"},
    "seeds": [
        {"id": 1, "type": "email", "value": "riley@example.com"},
        {"id": 2, "type": "username", "value": "riley.case"},
    ],
    "observations": [
        {"id": 10, "type": "profile_url", "value": "https://example.com/riley.case", "confidence": 0.8, "source_ref": "connector:maigret", "evidence_ref": "ev-profile"},
        {"id": 11, "type": "email", "value": "riley@example.com", "confidence": 0.9, "source_ref": "connector:h8mail", "evidence_ref": "ev-email"},
    ],
}
profile_payload = {
    "candidates": [
        {
            "candidate_id": "cand-ready",
            "identity_score": 0.91,
            "evidence_refs": ["ev-profile"],
            "source_connector": "maigret",
            "analyst_review": {"review_state": "accepted"},
            "dossier_assertion_gate": {"dossier_ready": True},
            "evidence_capture": {"capture_id": "cap-ready"},
            "profile_fingerprint": {
                "username": "riley.case",
                "platform": "example.com",
                "profile_url": "https://example.com/riley.case",
                "html_sha256": "h" * 64,
                "metadata_sha256": "m" * 64,
                "source_connectors": ["maigret"],
            },
        },
        {
            "candidate_id": "cand-blocked",
            "identity_score": 0.42,
            "evidence_refs": ["ev-blocked"],
            "analyst_review": {"review_state": "needs_more_evidence"},
            "dossier_assertion_gate": {"dossier_ready": False},
            "profile_fingerprint": {
                "username": "riley.other",
                "platform": "example.net",
                "profile_url": "https://example.net/riley.other",
                "source_connectors": ["sherlock"],
            },
        },
    ]
}

alias_graph = build_entity_alias_graph(payload, profile_payload)
identity_links = build_identity_link_hypotheses(alias_graph, profile_payload)
projection = build_dossier_assertion_projection(identity_links, alias_graph)
packet = build_dossier_assertion_review_packet(projection)
print(packet["schema"])
print(packet["ready_packet_count"], packet["blocked_packet_count"])
assert packet["schema"] == "socmint.dossier_assertion_review_packet.v12_10_9"
assert packet["packet_count"] == 2
assert packet["ready_packet_count"] == 1
assert packet["blocked_packet_count"] == 1
ready = next(row for row in packet["packets"] if row["candidate_id"] == "cand-ready")
assert ready["review_state"] == "ready_for_analyst"
assert ready["recommended_action"] == "review_for_confirmation"
assert not ready["blockers"]
assert any(check["name"] == "analyst_confirmation_required" and check["status"] == "review" for check in ready["checklist"])
blocked = next(row for row in packet["packets"] if row["candidate_id"] == "cand-blocked")
assert blocked["review_state"] == "blocked"
assert blocked["recommended_action"] == "resolve_blockers"
assert blocked["blockers"]

mime, name, body = export_dossier_assertion_review_packet_report(packet, "md")
assert mime == "text/markdown"
assert name == "dossier-assertion-review-packet.md"
assert "Dossier Assertion Review Packet" in body
assert "Ready packets: 1" in body
print("PASS dossier assertion review packet smoke")
PY
