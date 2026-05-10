
from pathlib import Path

from socmint.dashboard import create_app
from socmint.evidence_custody import chain_of_custody_report
from socmint.evidence_custody import custody_payload
from socmint.evidence_custody import record_custody_event
from socmint.evidence_custody import verify_all_evidence
from socmint.evidence_intake import intake_evidence_file
from socmint.evidence_links import link_evidence_to_review_item


def test_custody_event_recorded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    event = record_custody_event(
        evidence_id="abc123",
        action="manual_review",
        actor="tester",
        sha256="abc",
        status="ok",
        note="checked",
    )

    assert event["evidence_id"] == "abc123"
    assert event["action"] == "manual_review"

    payload = custody_payload(evidence_id="abc123")
    assert payload["schema"] == "socmint.chain_of_custody_payload.v7_4_2"
    assert payload["event_count"] == 1


def test_intake_and_link_create_custody_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "custody.txt"
    source.write_text("custody data")

    evidence = intake_evidence_file(source, case_id="case-custody")

    link_evidence_to_review_item(
        evidence_id=evidence["evidence_id"],
        review_item_id="findings:42",
        relation="supports",
        note="custody link",
    )

    payload = custody_payload(evidence_id=evidence["evidence_id"])
    actions = {event["action"] for event in payload["events"]}

    assert "intake" in actions
    assert "link" in actions


def test_hash_verification_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    source = tmp_path / "verify.pdf"
    source.write_bytes(b"verify me")

    intake_evidence_file(source, case_id="case-verify", subject_id=77)

    report = verify_all_evidence(
        case_id="case-verify",
        subject_id=77,
        actor="tester",
    )

    assert report["schema"] == "socmint.hash_verification_report.v7_4_2"
    assert report["checked_count"] == 1
    assert report["verified_count"] == 1
    assert Path(report["report_path"]).exists()
    assert Path(report["markdown_path"]).exists()

    payload = custody_payload(action="verify")
    assert payload["event_count"] == 1


def test_chain_of_custody_report_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    record_custody_event("abc123", "manual_review", note="report me")

    report = chain_of_custody_report()

    assert report["schema"] == "socmint.chain_of_custody_payload.v7_4_2"
    assert Path(report["report_path"]).exists()
    assert Path(report["markdown_path"]).exists()


def test_custody_routes_registered():
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/evidence/custody" in rules
    assert "/api/v1/evidence/custody" in rules
    assert "/api/v1/evidence/verify" in rules
    assert "/evidence/verify/run" in rules
    assert "/api/v1/evidence/custody/report" in rules
