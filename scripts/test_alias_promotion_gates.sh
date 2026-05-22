#!/usr/bin/env bash
set -euo pipefail

echo "[+] Alias promotion gates smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.alias_promotion_gates_v12_10_7_1 import (
    apply_promotion_gates_to_alias_graph,
    classify_observation_type,
    is_asset_only_url,
    phone_rejection_reason,
    promotion_gate_for_observation,
)
from src.socmint.spine_intelligence_v11_9 import _dossier_readiness_gate

assert is_asset_only_url("https://tr.rbxcdn.com/30DAY-Avatar-abc-png/352/352/avatar/png/nofilter")
assert classify_observation_type("profile_url", "https://tr.rbxcdn.com/30DAY-Avatar-abc.png")[0] == "avatar_url"
assert classify_observation_type("profile_url", "https://s.pinimg.com/images/default_open_graph_1200.png")[0] == "static_asset_url"

assert phone_rejection_reason("2023-10-29 20") == "rejected_timestamp"
assert phone_rejection_reason("4.8429296016693115") == "rejected_not_phone"
assert phone_rejection_reason("844727197231394817") == "rejected_platform_artifact_id"

gate = promotion_gate_for_observation({"type": "profile_url", "value": "https://yt3.googleusercontent.com/ytc/avatar=s900"})
assert gate["blocked"] is True
assert "rejected_asset_only_url" in gate["reason_labels"]
assert gate["ui_badge"] == "Promotion blocked: not identity evidence"

graph = {
    "aliases": [
        {
            "alias_id": "a1",
            "alias_type": "url",
            "normalized_value": "https://pbs.twimg.com/profile_images/123/avatar.jpg",
            "analyst_state": "candidate",
            "can_promote_to_dossier_assertion": True,
        },
        {
            "alias_id": "a2",
            "alias_type": "phone",
            "normalized_value": "1779505200",
            "analyst_state": "candidate",
            "can_promote_to_dossier_assertion": True,
        },
    ]
}
graph = apply_promotion_gates_to_alias_graph(graph)
assert graph["promotion_gates"]["blocked_alias_count"] == 2
assert all(not a["can_promote_to_dossier_assertion"] for a in graph["aliases"])

gate = _dossier_readiness_gate(
    [{"validation_state": "confirmed"}],
    {"needs_review_count": 38, "review_decision_counts": {}, "evidence_capture": {}},
    {"collision_count": 41, "alias_review": {"decision_counts": {}, "clusters": {}}, "promotion_gates": {}},
)
assert gate["status"] == "hold"
assert "candidate_profile_review_remaining" in gate["hard_holds"]
assert "alias_collisions_unreviewed" in gate["hard_holds"]

print("PASS alias promotion gates smoke")
PY
