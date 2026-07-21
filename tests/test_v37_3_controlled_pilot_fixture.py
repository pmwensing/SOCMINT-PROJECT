import json
from pathlib import Path

from src.socmint.cases.entity_scope_filter import ScopeStatus, evaluate_text_scope


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/v37_imports/fictional_46_montreal_pilot.json"


def test_v37_3_controlled_pilot_fixture_exercises_all_scope_classes():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    records = payload["records"]
    assert len(records) == 4
    statuses = {
        item["source_record_id"]: evaluate_text_scope(
            " ".join(
                [
                    str(item["raw_value"]),
                    str(item["normalized_value"]),
                    " ".join(str(value) for value in item["context"].values()),
                ]
            )
        ).status
        for item in records
    }
    assert statuses == {
        "pilot-direct": ScopeStatus.IN_SCOPE,
        "pilot-relocation": ScopeStatus.RELOCATION_CONTEXT,
        "pilot-excluded": ScopeStatus.OUT_OF_SCOPE,
        "pilot-candidate": ScopeStatus.CANDIDATE_REVIEW_REQUIRED,
    }


def test_v37_3_public_fixture_contains_no_private_storage_or_credentials():
    text = FIXTURE.read_text(encoding="utf-8").lower()
    prohibited = (
        "e:\\",
        "c:/",
        "c:\\",
        "onedrive",
        "google drive",
        "terabox",
        "password",
        "token",
        "cookie",
        "authorization",
        "private_url",
        "share_link",
    )
    for marker in prohibited:
        assert marker not in text
    assert '"synthetic_fixture": true' in text


def test_v37_3_case_configuration_preserves_pilot_boundaries():
    case_config = (ROOT / "config/cases/46_montreal.case.yaml").read_text(
        encoding="utf-8"
    )
    assert "case_46_montreal" in case_config
    assert "candidate_entities_require_review: true" in case_config
    assert "559 Macdonnel" in case_config
    assert "role: suitable bungalow relocation" in case_config
    assert "no_unscoped_export: true" in case_config
