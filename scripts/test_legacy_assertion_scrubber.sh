#!/usr/bin/env bash
set -euo pipefail

echo "[+] Legacy assertion scrubber smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.legacy_assertion_scrubber_v12_10_7_2 import (
    apply_assertion_scrub_gate,
    scrub_summary,
)

asset = apply_assertion_scrub_gate({
    "id": 1,
    "type": "profile_url",
    "value": "https://assets.tumblr.com/images/default_avatar/cone_closed_512.png",
    "validation_state": "unreviewed",
    "payload": {},
})
assert asset["validation_state"] == "suppressed"
assert asset["legacy_assertion_scrub"]["blocked"] is True
assert "rejected_asset_only_url" in asset["legacy_assertion_scrub"]["reason_labels"]

phone = apply_assertion_scrub_gate({
    "id": 2,
    "type": "phone",
    "value": "2023-10-29 20",
    "validation_state": "unreviewed",
    "payload": {},
})
assert phone["validation_state"] == "suppressed"
assert phone["type"] == "metadata_artifact"
assert "rejected_timestamp" in phone["legacy_assertion_scrub"]["reason_labels"]

platform_id = apply_assertion_scrub_gate({
    "id": 3,
    "type": "phone",
    "value": "844727197231394817",
    "validation_state": "unreviewed",
    "payload": {},
})
assert platform_id["validation_state"] == "suppressed"
assert platform_id["type"] == "platform_artifact_id"
assert "rejected_platform_artifact_id" in platform_id["legacy_assertion_scrub"]["reason_labels"]

email = apply_assertion_scrub_gate({
    "id": 4,
    "type": "email",
    "value": "samantha4432@hotmail.com",
    "validation_state": "confirmed",
    "payload": {},
})
assert email["validation_state"] == "confirmed"
assert email["legacy_assertion_scrub"]["blocked"] is False

summary = scrub_summary(
    [asset, phone, platform_id, email],
    [{"promotion_blocked": True, "promotion_block_reason_labels": ["rejected_asset_only_url"]}],
    {"promotion_gates": {"blocked_alias_count": 2, "reason_counts": {"rejected_asset_only_url": 2}}},
)
assert summary["blocked_assertion_count"] == 3
assert summary["blocked_observation_count"] == 1
assert summary["blocked_alias_count"] == 2
assert summary["blocked_total_count"] == 6

print("PASS legacy assertion scrubber smoke")
PY
