from src.socmint import database as db


def test_connector_run_and_findings_persist(tmp_path):
    db_path = tmp_path / "socmint.db"
    db.configure_database(f"sqlite:///{db_path}")

    run_id = db.record_connector_run(
        target_value="alice",
        target_type="username",
        connector="sherlock",
        raw_result={
            "connector": "sherlock",
            "status": "completed",
            "command": ["sherlock", "alice"],
            "stdout": "https://example.com/alice",
            "stderr": "",
            "findings": [
                {
                    "type": "url",
                    "value": "https://example.com/alice",
                    "source": "sherlock",
                    "confidence": 0.75,
                }
            ],
        },
    )

    runs = db.list_connector_runs()
    findings = db.list_findings()

    assert run_id
    assert runs[0].connector == "sherlock"
    assert findings[0].type == "url"
    assert "example.com/alice" in findings[0].value
