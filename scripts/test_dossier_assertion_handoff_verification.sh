#!/usr/bin/env bash
set -euo pipefail

echo "[+] Dossier assertion handoff verification smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.dossier_assertion_handoff_bundle_v12_10_10 import build_dossier_assertion_handoff_bundle
from src.socmint.dossier_assertion_handoff_seal_v12_10_11 import build_dossier_assertion_handoff_seal
from src.socmint.dossier_assertion_handoff_verification_v12_10_12 import build_dossier_assertion_handoff_verification, export_dossier_assertion_handoff_verification_report
from src.socmint.dossier_assertion_projection_v12_10_8 import build_dossier_assertion_projection
from src.socmint.dossier_assertion_review_packet_v12_10_9 import build_dossier_assertion_review_packet
from src.socmint.entity_alias_graph_v12_10_6 import build_entity_alias_graph
from src.socmint.identity_link_hypothesis_v12_10_7 import build_identity_link_hypotheses

payload = {
    "subject": {"id": 12, "label": "Subject"},
    "seeds": [
        {"id": 1, "type": "email", "value": "jordan@example.com"},
        {"id": 2, "type": "username", "value": "jordan.case"},
    ],
    "observations": [
        {"id": 10, "type": "profile_url", "value": "https://example.com/jordan.case", "confidence": 0.85, "source_ref": "connector:maigret", "evidence_ref": "ev-profile"},
        {"id": 11, "type": "email", "value": "jordan@example.com", "confidence": 0.94, "source_ref": "connector:h8mail", "evidence_ref": "ev-email"},
    ],
}
profile_payload = {
    "candidates": [
        {
            "candidate_id": "cand-ready",
            "identity_score": 0.95,
            "evidence_refs": ["ev-profile"],
            "source_connector": "maigret",
            "analyst_review": {"review_state": "accepted"},
            "dossier_assertion_gate": {"dossier_ready": True},
            "evidence_capture": {"capture_id": "cap-ready"},
            "profile_fingerprint": {
                "username": "jordan.case",
                "platform": "example.com",
                "profile_url": "https://example.com/jordan.case",
                "html_sha256": "h" * 64,
                "metadata_sha256": "m" * 64,
                "source_connectors": ["maigret"],
            },
        }
    ]
}

alias_graph = build_entity_alias_graph(payload, profile_payload)
identity_links = build_identity_link_hypotheses(alias_graph, profile_payload)
projection = build_dossier_assertion_projection(identity_links, alias_graph)
packet = build_dossier_assertion_review_packet(projection)
bundle = build_dossier_assertion_handoff_bundle(packet)
seal = build_dossier_assertion_handoff_seal(bundle)
verification = build_dossier_assertion_handoff_verification(bundle, seal)
print(verification["schema"])
print(verification["status"], verification["failure_count"])
assert verification["schema"] == "socmint.dossier_assertion_handoff_verification.v12_10_12"
assert verification["status"] == "pass"
assert verification["failure_count"] == 0
assert any(check["name"] == "manual_review_required" and check["status"] == "review" for check in verification["checks"])

bad_seal = dict(seal)
bad_seal["packet_count"] = 999
assert build_dossier_assertion_handoff_verification(bundle, bad_seal)["status"] == "fail"

mime, name, body = export_dossier_assertion_handoff_verification_report(verification, "md")
assert mime == "text/markdown"
assert name == "dossier-assertion-handoff-verification.md"
assert "Dossier Assertion Handoff Verification" in body
assert "Status: pass" in body
print("PASS dossier assertion handoff verification smoke")
PY
