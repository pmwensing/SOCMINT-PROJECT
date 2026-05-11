from src.socmint import database as db
from src.socmint.evidence import assertion_review_queue
from src.socmint.jobs import cancel_scan_job
from src.socmint.jobs import requeue_scan_job
from src.socmint.jobs import scan_job_health
from src.socmint.spine import create_subject
from src.socmint.ultimate_dossier import dossier_export_manifest
from src.socmint.ultimate_dossier import redacted_dossier_payload
from src.socmint.ultimate_dossier import ultimate_dossier_payload


def test_ultimate_dossier_manifest_redaction_and_readiness(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    subject_id = create_subject(
        "Hardening Subject",
        [{"type": "email", "value": "hardening@example.com"}],
    )

    payload = ultimate_dossier_payload(subject_id)
    manifest = dossier_export_manifest(payload, redacted=True)
    redacted = redacted_dossier_payload(payload)

    assert payload["readiness"]["state"] == "blocked"
    assert manifest["schema"] == "socmint.ultimate_entity_human_dossier_manifest.v7_8_1"
    assert manifest["redacted"] is True
    assert manifest["parity"]["csv_matches_assertions"] is True
    assert redacted["redaction"]["mode"] == "sensitive_identifiers"


def test_scan_job_health_requeue_and_cancel(tmp_path, monkeypatch):
    db.configure_database(f"sqlite:///{tmp_path / 'jobs.db'}")
    job = db.create_scan_job("operator_job", "username", tools={"sherlock"})

    health = scan_job_health()
    assert health["queue_depth"] == 1
    assert health["needs_attention"] is False

    canceled = cancel_scan_job(job.id, reason="test cancel")
    assert canceled["status"] == "canceled"
    assert db.get_scan_job(job.id).error == "test cancel"

    requeued = requeue_scan_job(job.id)
    assert requeued["status"] == "queued"
    assert db.get_scan_job(job.id).error is None


def test_assertion_review_queue_prioritizes_unreviewed(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    db.configure_database(f"sqlite:///{tmp_path / 'review.db'}")
    subject_id = create_subject(
        "Review Subject",
        [{"type": "username", "value": "reviewuser"}],
    )
    assertion_id = db.upsert_spine_assertion(
        subject_id=subject_id,
        assertion_type="profile_url",
        normalized_value="https://example.com/reviewuser",
        confidence="0.82",
        validation_state="unreviewed",
        payload={"source_refs": ["run:1:sherlock"]},
    )

    queue = assertion_review_queue()

    assert queue[0]["id"] == assertion_id
    assert queue[0]["priority"] >= 70
    assert "unreviewed" in queue[0]["reasons"]
