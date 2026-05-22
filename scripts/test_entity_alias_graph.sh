#!/usr/bin/env bash
set -euo pipefail

echo "[+] Entity alias graph smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.entity_alias_graph_v12_10_6 import build_entity_alias_graph, normalize_alias, export_entity_alias_graph_report

assert normalize_alias("email", "Sam@Example.COM") == "sam@example.com"
assert normalize_alias("username", "@Samantha4432") == "samantha4432"
assert normalize_alias("phone", "+1 (613) 555-1212") == "16135551212"
assert normalize_alias("domain", "https://www.Example.com/profile/sam") == "example.com"

payload = {
    "subject": {"id": 3, "label": "Subject"},
    "seeds": [
        {"id": 1, "type": "email", "value": "samantha4432@hotmail.com"},
        {"id": 2, "type": "username", "value": "sam.alt"},
        {"id": 3, "type": "phone", "value": "+1 613 555 1212"},
    ],
    "observations": [
        {"id": 10, "type": "profile_url", "value": "https://example.com/samantha4432", "confidence": 0.7, "source_ref": "connector:maigret", "evidence_ref": "ev-1"},
        {"id": 11, "type": "username", "value": "samantha4432", "confidence": 0.6, "source_ref": "connector:sherlock", "evidence_ref": "ev-2"},
        {"id": 12, "type": "email", "value": "samantha4432@hotmail.com", "confidence": 0.85, "source_ref": "connector:h8mail", "evidence_ref": "ev-3"},
    ],
}
profile_payload = {
    "candidates": [
        {
            "candidate_id": "cand-1",
            "identity_score": 0.82,
            "collision_status": "likely_same_online_identity",
            "evidence_refs": ["ev-1"],
            "source_connector": "maigret",
            "analyst_review": {"review_state": "accepted"},
            "dossier_assertion_gate": {"dossier_ready": True},
            "profile_fingerprint": {
                "username": "samantha4432",
                "platform": "example.com",
                "profile_url": "https://example.com/samantha4432",
                "linked_urls": ["https://links.example.org/@sam"],
                "avatar_phash": "avatarhash1",
                "visual_fingerprint_hash": "visualhash1",
                "text_fingerprint_hash": "texthash1",
                "source_connectors": ["maigret"],
            },
        },
        {
            "candidate_id": "cand-2",
            "identity_score": 0.05,
            "collision_status": "asset_only_not_profile",
            "evidence_refs": ["ev-asset"],
            "analyst_review": {"review_state": "unreviewed"},
            "dossier_assertion_gate": {"suppressed": True, "dossier_ready": False},
            "profile_fingerprint": {
                "username": "30day-avatar",
                "platform": "tr.rbxcdn.com",
                "profile_url": "https://tr.rbxcdn.com/30DAY-Avatar.png",
                "asset_only_url": True,
                "visual_fingerprint_hash": "visualhash1",
                "source_connectors": ["social-analyzer"],
            },
        },
    ]
}

graph = build_entity_alias_graph(payload, profile_payload)
print(graph["schema"])
print(graph["alias_count"], graph["edge_count"], graph["collision_count"])
assert graph["schema"] == "socmint.entity_alias_graph.v12_10_6"
assert graph["alias_count"] >= 10
assert graph["type_counts"]["email"] >= 1
assert graph["type_counts"]["username"] >= 2
assert graph["type_counts"]["url"] >= 2
assert graph["state_counts"]["confirmed"] >= 3
assert graph["state_counts"]["rejected"] >= 1
assert any(c["status"] in {"reverse_collision_review", "rejected_or_suppressed"} for c in graph["collision_sets"])

mime, name, body = export_entity_alias_graph_report(graph, "md")
assert mime == "text/markdown"
assert name == "entity-alias-graph-subject-3.md"
assert "Entity Alias Graph" in body
assert "One entity may have many aliases" in body

print("PASS entity alias graph smoke")
PY
