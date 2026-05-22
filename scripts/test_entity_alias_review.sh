#!/usr/bin/env bash
set -euo pipefail

echo "[+] Entity alias review smoke"
PYTHONPATH=src SOCMINT_ARTIFACT_DIR="${SOCMINT_ARTIFACT_DIR:-/tmp/socmint-v12-10-7-artifacts}" python3 - <<'PY'
import os
import tempfile

os.environ["SOCMINT_ARTIFACT_DIR"] = tempfile.mkdtemp(prefix="socmint-v12-10-7-")

from src.socmint.entity_alias_graph_v12_10_6 import build_entity_alias_graph
from src.socmint.entity_alias_review_v12_10_7 import (
    apply_alias_review_decisions,
    merge_alias_cluster,
    review_entity_alias,
    split_alias_from_clusters,
)

payload = {
    "subject": {"id": 3, "label": "Subject"},
    "seeds": [
        {"id": 1, "type": "email", "value": "samantha4432@hotmail.com"},
        {"id": 2, "type": "username", "value": "samantha4432"},
    ],
    "observations": [
        {"id": 10, "type": "profile_url", "value": "https://example.com/samantha4432", "confidence": 0.7, "source_ref": "connector:maigret", "evidence_ref": "ev-1"},
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
                "visual_fingerprint_hash": "visualhash1",
                "text_fingerprint_hash": "texthash1",
                "source_connectors": ["maigret"],
            },
        }
    ]
}

graph = build_entity_alias_graph(payload, profile_payload)
email_alias = next(a for a in graph["aliases"] if a["alias_type"] == "email")
username_alias = next(a for a in graph["aliases"] if a["alias_type"] == "username" and a["normalized_value"] == "samantha4432")
url_alias = next(a for a in graph["aliases"] if a["alias_type"] == "url" and a["normalized_value"] == "https://example.com/samantha4432")

result = review_entity_alias(3, email_alias["alias_id"], "confirm_alias", graph, actor="tester", note="seed email confirmed")
assert result["review_state"] == "confirmed"
result = review_entity_alias(3, url_alias["alias_id"], "mark_alias_uncertain", graph, actor="tester", note="needs corroboration")
assert result["review_state"] == "uncertain"

cluster = merge_alias_cluster(3, [email_alias["alias_id"], username_alias["alias_id"]], graph, actor="tester", note="same entity alias set")
assert len(cluster["alias_ids"]) == 2

reviewed = apply_alias_review_decisions(graph, 3)
email_after = next(a for a in reviewed["aliases"] if a["alias_id"] == email_alias["alias_id"])
url_after = next(a for a in reviewed["aliases"] if a["alias_id"] == url_alias["alias_id"])
username_after = next(a for a in reviewed["aliases"] if a["alias_id"] == username_alias["alias_id"])
assert email_after["analyst_state"] == "confirmed"
assert email_after["can_promote_to_dossier_assertion"] is True
assert url_after["analyst_state"] == "uncertain"
assert url_after["can_promote_to_dossier_assertion"] is False
assert cluster["cluster_id"] in username_after["identity_cluster_ids"]

split = split_alias_from_clusters(3, username_alias["alias_id"], actor="tester", note="bad alias split")
assert cluster["cluster_id"] in split["split_from_clusters"]
reviewed = apply_alias_review_decisions(graph, 3)
username_after = next(a for a in reviewed["aliases"] if a["alias_id"] == username_alias["alias_id"])
assert cluster["cluster_id"] not in username_after["identity_cluster_ids"]
assert reviewed["alias_review"]["promotable_alias_count"] >= 1

print("PASS entity alias review smoke")
PY
