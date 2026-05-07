import pytest

from src.socmint import database as db
from src.socmint.spine import create_subject
from src.socmint.workbench import create_workbench_job
from src.socmint.workbench import evaluate_policy
from src.socmint.workbench import run_retention
from src.socmint.workbench import run_workbench_job
from src.socmint.workbench import workbench_status


@pytest.fixture()
def configured_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SOCMINT_EXPORT_DIR", str(tmp_path / "exports"))
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    return db


def test_policy_rejects_unknown_job(configured_db):
    decision = evaluate_policy(
        "create_job",
        {"job_type": "unknown", "subject_id": 1},
    )

    assert decision["allowed"] is False
    assert decision["event_id"]


def test_workbench_job_runs_dossier_export(configured_db, monkeypatch):
    def fake_execute_connector(connector_key, seed):
        return {
            "connector": connector_key,
            "status": "dry_run",
            "findings": [
                {
                    "type": "account_presence",
                    "value": f"https://example.com/{seed.normalized_value}",
                    "source": connector_key,
                    "confidence": 0.61,
                }
            ],
        }

    monkeypatch.setattr("src.socmint.spine.execute_connector", fake_execute_connector)

    subject_id = create_subject(
        "Workbench Subject",
        [{"type": "username", "value": "exampleuser"}],
    )
    job_id = create_workbench_job(
        job_type="full_dossier_pipeline",
        subject_id=subject_id,
        payload={"connectors": ["sherlock"], "formats": ["json", "html", "pdf"]},
        actor="tester",
    )

    result = run_workbench_job(job_id, actor="tester")
    status = workbench_status()
    job = db.get_workbench_job(job_id)

    assert result["export"]["files"]
    assert status["by_status"]["completed"] == 1
    assert job.status == "completed"


def test_retention_dry_run(configured_db):
    result = run_retention(mode="dry_run", actor="tester")

    assert result["retention_run_id"]
    assert result["mode"] == "dry_run"


def test_workbench_api(tmp_path, monkeypatch):
    from src.socmint.dashboard import create_app

    monkeypatch.setenv(
        "SOCMINT_SECRET_KEY",
        "test-secret-key-for-socmint-spine-32chars-plus",
    )
    monkeypatch.setenv("SOCMINT_ADMIN_USER", "admin")
    monkeypatch.setenv("SOCMINT_ADMIN_PASSWORD", "StrongPass123!")
    monkeypatch.setenv("SOCMINT_AUTO_CREATE_DB", "1")
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SOCMINT_EXPORT_DIR", str(tmp_path / "exports"))

    app = create_app(database_url=f"sqlite:///{tmp_path / 'web.db'}")
    app.config.update(TESTING=True)
    client = app.test_client()
    csrf = "test-csrf-token"

    with client.session_transaction() as sess:
        sess["_csrf_token"] = csrf

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "StrongPass123!",
            "csrf_token": csrf,
        },
    )

    created = client.post(
        "/api/v1/spine/subjects",
        json={
            "label": "Workbench Web Subject",
            "seeds": [{"type": "username", "value": "exampleuser"}],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    subject_id = created.get_json()["subject_id"]

    job = client.post(
        "/api/v1/workbench/jobs",
        json={
            "subject_id": subject_id,
            "job_type": "dossier_export",
            "payload": {"formats": ["json"]},
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert job.status_code == 201
    job_id = job.get_json()["job_id"]

    run = client.post(
        f"/api/v1/workbench/jobs/{job_id}/run",
        headers={"X-CSRF-Token": csrf},
    )
    assert run.status_code == 202
    assert run.get_json()["files"]

    status = client.get("/api/v1/workbench/status")
    assert status.status_code == 200
    assert status.get_json()["jobs_total"] == 1

    retention = client.post(
        "/api/v1/workbench/retention/run",
        json={"mode": "dry_run"},
        headers={"X-CSRF-Token": csrf},
    )
    assert retention.status_code == 202
    assert retention.get_json()["mode"] == "dry_run"
