#!/usr/bin/env bash
set -euo pipefail

echo "[+] Dossier assertion projection smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.dossier_assertion_projection_v12_10_8 import build_dossier_assertion_projection, export_dossier_assertion_projection_report
from src.socmint.entity_alias_graph_v12_10_6 import build_entity_alias_graph
from src.socmint.identity_link_hypothesis_v12_10_7 import build_identity_link_hypotheses

payload = {
    "subject": {"id": 8, "label": "Subject"},
    "seeds": [
        {"id": 1, "type": "email", "value": "casey@example.com"},
        {"id": 2, "type": "username", "value": "casey.profile"},
    ],
    "observations": [
        {"id": 10, "type": "profile_url", "value": "https://example.com/casey.profile", "confidence": 0.8, "source_ref": "connector:maigret", "evidence_ref": "ev-profile"},
        {"id": 11, "type": "email", "value": "casey@example.com", "confidence": 0.9, "source_ref": "connector:h8mail", "evidence_ref": "ev-email"},
    ],
}
profile_payload = {
    "candidates": [
        {
            "candidate_id": "cand-ready",
            "identity_score": 0.9,
            "evidence_refs": ["ev-profile"],
            "source_connector": "maigret",
            "analyst_review": {"review_state": "accepted"},
            "dossier_assertion_gate": {"dossier_ready": True},
            "evidence_capture": {"capture_id": "cap-ready"},
            "profile_fingerprint": {
                "username": "casey.profile",
                "platform": "example.com",
                "profile_url": "https://example.com/casey.profile",
                "html_sha256": "h" * 64,
                "metadata_sha256": "m" * 64,
                "source_connectors": ["maigret"],
            },
        },
        {
            "candidate_id": "cand-blocked",
            "identity_score": 0.45,
            "evidence_refs": ["ev-blocked"],
            "analyst_review": {"review_state": "uncertain"},
            "dossier_assertion_gate": {"dossier_ready": False},
            "profile_fingerprint": {
                "username": "casey.other",
                "platform": "example.net",
                "profile_url": "https://example.net/casey.other",
                "source_connectors": ["sherlock"],
            },
        },
    ]
}

alias_graph = build_entity_alias_graph(payload, profile_payload)
identity_links = build_identity_link_hypotheses(alias_graph, profile_payload)
projection = build_dossier_assertion_projection(identity_links, alias_graph)
print(projection["schema"])
print(projection["ready_count"], projection["blocked_count"])
assert projection["schema"] == "socmint.dossier_assertion_projection.v12_10_8"
assert projection["projection_count"] == 2
assert projection["ready_count"] == 1
assert projection["blocked_count"] == 1
ready = next(row for row in projection["projections"] if row["candidate_id"] == "cand-ready")
assert ready["status"] == "ready"
assert ready["dossier_ready"] is True
assert "ev-profile" in ready["evidence_refs"]
assert "same_entity_profile" == ready["assertion_type"]
blocked = next(row for row in projection["projections"] if row["candidate_id"] == "cand-blocked")
assert blocked["status"] == "blocked"
assert blocked["dossier_ready"] is False

mime, name, body = export_dossier_assertion_projection_report(projection, "md")
assert mime == "text/markdown"
assert name == "dossier-assertion-projection.md"
assert "Dossier Assertion Projection" in body
assert "Ready: 1" in body
print("PASS dossier assertion projection smoke")
PY
