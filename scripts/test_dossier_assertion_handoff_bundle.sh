#!/usr/bin/env bash
set -euo pipefail

echo "[+] Dossier assertion handoff bundle smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.dossier_assertion_handoff_bundle_v12_10_10 import build_dossier_assertion_handoff_bundle, export_dossier_assertion_handoff_bundle_report
from src.socmint.dossier_assertion_projection_v12_10_8 import build_dossier_assertion_projection
from src.socmint.dossier_assertion_review_packet_v12_10_9 import build_dossier_assertion_review_packet
from src.socmint.entity_alias_graph_v12_10_6 import build_entity_alias_graph
from src.socmint.identity_link_hypothesis_v12_10_7 import build_identity_link_hypotheses

payload = {
    "subject": {"id": 10, "label": "Subject"},
    "seeds": [
        {"id": 1, "type": "email", "value": "morgan@example.com"},
        {"id": 2, "type": "username", "value": "morgan.case"},
    ],
    "observations": [
        {"id": 10, "type": "profile_url", "value": "https://example.com/morgan.case", "confidence": 0.82, "source_ref": "connector:maigret", "evidence_ref": "ev-profile"},
        {"id": 11, "type": "email", "value": "morgan@example.com", "confidence": 0.92, "source_ref": "connector:h8mail", "evidence_ref": "ev-email"},
    ],
}
profile_payload = {
    "candidates": [
        {
            "candidate_id": "cand-ready",
            "identity_score": 0.93,
            "evidence_refs": ["ev-profile"],
            "source_connector": "maigret",
            "analyst_review": {"review_state": "accepted"},
            "dossier_assertion_gate": {"dossier_ready": True},
            "evidence_capture": {"capture_id": "cap-ready"},
            "profile_fingerprint": {
                "username": "morgan.case",
                "platform": "example.com",
                "profile_url": "https://example.com/morgan.case",
                "html_sha256": "h" * 64,
                "metadata_sha256": "m" * 64,
                "source_connectors": ["maigret"],
            },
        },
        {
            "candidate_id": "cand-blocked",
            "identity_score": 0.39,
            "evidence_refs": ["ev-blocked"],
            "analyst_review": {"review_state": "uncertain"},
            "dossier_assertion_gate": {"dossier_ready": False},
            "profile_fingerprint": {
                "username": "morgan.other",
                "platform": "example.net",
                "profile_url": "https://example.net/morgan.other",
                "source_connectors": ["sherlock"],
            },
        },
    ]
}

alias_graph = build_entity_alias_graph(payload, profile_payload)
identity_links = build_identity_link_hypotheses(alias_graph, profile_payload)
projection = build_dossier_assertion_projection(identity_links, alias_graph)
packet = build_dossier_assertion_review_packet(projection)
bundle = build_dossier_assertion_handoff_bundle(packet)
print(bundle["schema"])
print(bundle["ready_count"], bundle["blocked_count"])
assert bundle["schema"] == "socmint.dossier_assertion_handoff_bundle.v12_10_10"
assert bundle["total_count"] == 2
assert bundle["ready_count"] == 1
assert bundle["blocked_count"] == 1
assert bundle["ready_packets"][0]["candidate_id"] == "cand-ready"
assert bundle["blocked_packets"][0]["candidate_id"] == "cand-blocked"
assert bundle["next_actions"]

mime, name, body = export_dossier_assertion_handoff_bundle_report(bundle, "md")
assert mime == "text/markdown"
assert name == "dossier-assertion-handoff-bundle.md"
assert "Dossier Assertion Handoff Bundle" in body
assert "Ready: 1" in body
print("PASS dossier assertion handoff bundle smoke")
PY
