from __future__ import annotations

import json
from pathlib import Path


def test_v39_0_case_adapter_control_contract_is_non_authoritative():
    contract = json.loads(
        Path("release/V39_0_CASE_ADAPTER_CONTROL_PLANE.json").read_text(encoding="utf-8")
    )

    assert contract["version"] == "v39.0.0"
    assert contract["adapter"]["modes"] == ["off", "passive", "on"]
    assert contract["adapter"]["default_mode"] == "passive"
    assert contract["adapter"]["direct_off_to_on_allowed"] is False
    assert contract["scope"]["cowdy_street"] == {
        "upstairs_noise": True,
        "water_leak": True,
        "other_issues": False,
        "landlord_adverse_characterization": False,
    }

    reuse = contract["authoritative_reuse"]
    assert reuse["mode_history"] == "existing AuditLog"
    assert all(
        value is False
        for key, value in reuse.items()
        if key != "mode_history"
    )

    assert contract["next_action"] == "implement_v39_1_passive_inventory_and_scope_classifier"
