#!/usr/bin/env bash
set -euo pipefail

echo "[+] URL asset promotion gates smoke"
PYTHONPATH=src python3 - <<'PY'
from src.socmint.alias_promotion_gates_v12_10_7_1 import (
    classify_observation_type,
    promotion_gate_for_observation,
)
from src.socmint.legacy_assertion_scrubber_v12_10_7_2 import apply_assertion_scrub_gate

asset_urls = [
    "https://tr.rbxcdn.com/30DAY-Avatar-260729AE68D05D5100DE836CA3D0E606-Png/352/352/Avatar/Png/noFilter",
    "https://simg-ssl.duolingo.com/ssr-avatars/1294536029/SSR-ViAk9LCjhm",
    "https://yt3.googleusercontent.com/ytc/AIdro_lrC-XjiWgV1N7d4br1RFU96XVpPgQBasrDhMxoec0=s900-c-k-c0x00ffffff-no-rj",
    "https://p16-common-sign.tiktokcdn.com/tos-alisg-avt-0068/smg0384ac1e55ddd4894c80917f795e5871~tplv-tiktokx-cropcenter:720:720.jpeg?x-expires=1779505200",
    "https://pbs.twimg.com/profile_images/844727197231394817/wCgNiSx5.jpg",
]

for url in asset_urls:
    safe_type, reasons, blocked = classify_observation_type("url", url)
    assert blocked is True, url
    assert "rejected_asset_only_url" in reasons, url
    assert safe_type in {"avatar_url", "static_asset_url"}, (url, safe_type)

    gate = promotion_gate_for_observation({"type": "url", "value": url})
    assert gate["blocked"] is True, gate
    assert gate["ui_badge"] == "Promotion blocked: not identity evidence"
    assert "rejected_asset_only_url" in gate["reason_labels"]

    assertion = apply_assertion_scrub_gate({
        "id": 1,
        "type": "url",
        "value": url,
        "validation_state": "unreviewed",
        "payload": {},
    })
    assert assertion["validation_state"] == "suppressed", assertion
    assert assertion["type"] in {"avatar_url", "static_asset_url"}, assertion
    assert assertion["legacy_assertion_scrub"]["blocked"] is True

real_profile = promotion_gate_for_observation({
    "type": "url",
    "value": "https://www.roblox.com/user.aspx?username=samantha4432",
})
assert real_profile["blocked"] is False

print("PASS url asset promotion gates smoke")
PY
