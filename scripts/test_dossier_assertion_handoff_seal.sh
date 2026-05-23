#!/usr/bin/env bash
set -euo pipefail

echo "[+] Dossier assertion handoff seal smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.dossier_assertion_handoff_bundle_v12_10_10 import build_dossier_assertion_handoff_bundle
from src.socmint.dossier_assertion_handoff_seal_v12_10_11 import build_dossier_assertion_handoff_seal, export_dossier_assertion_handoff_seal_report, verify_dossier_assertion_handoff_seal
from src.socmint.dossier_assertion_projection_v12_10_8 import build_dossier_assertion_projection
from src.socmint.dossier_assertion_review_packet_v12_10_9 import build_dossier_assertion_review_packet
from src.socmint.entity_alias_graph_v12_10_6 import build_entity_alias_graph
from src.socmint.identity_link_hypothesis_v12_10_7 import build_identity_link_hypotheses

payload = {
    "subject": {"id": 11, "label": "Subject"},
    "seeds": [
        {"id": 1, "type": "email", "value": "alex@example.com"},
        {"id": 2, "type": "username", "value": "alex.case"},
    ],
    "observations": [
        {"id": 10, "type": "profile_url", "value": "https://example.com/alex.case", "confidence": 0.84, "source_ref": "connector:maigret", "evidence_ref": "ev-profile"},
        {"id": 11, "type": "email", "value": "alex@example.com", "confidence": 0.93, "source_ref": "connector:h8mail", "evidence_ref": "ev-email"},
    ],
}
profile_payload = {
    "candidates": [
        {
            "candidate_id": "cand-ready",
            "identity_score": 0.94,
            "evidence_refs": ["ev-profile"],
            "source_connector": "maigret",
            "analyst_review": {"review_state": "accepted"},
            "dossier_assertion_gate": {"dossier_ready": True},
            "evidence_capture": {"capture_id": "cap-ready"},
            "profile_fingerprint": {
                "username": "alex.case",
                "platform": "example.com",
                "profile_url": "https://example.com/alex.case",
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
verification = verify_dossier_assertion_handoff_seal(bundle, seal)
print(seal["schema"])
print(seal["bundle_hash_sha256"])
assert seal["schema"] == "socmint.dossier_assertion_handoff_seal.v12_10_11"
assert len(seal["bundle_hash_sha256"]) == 64
assert len(seal["ready_hash_sha256"]) == 64
assert seal["packet_count"] == 1
assert verification["status"] == "pass"

tampered = dict(seal)
tampered["bundle_hash_sha256"] = "0" * 64
assert verify_dossier_assertion_handoff_seal(bundle, tampered)["status"] == "fail"

mime, name, body = export_dossier_assertion_handoff_seal_report(seal, "md")
assert mime == "text/markdown"
assert name == "dossier-assertion-handoff-seal.md"
assert "Dossier Assertion Handoff Seal" in body
assert "Bundle SHA-256" in body
print("PASS dossier assertion handoff seal smoke")
PY
