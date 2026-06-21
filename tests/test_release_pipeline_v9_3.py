from src.socmint.release_pipeline import release_pipeline_check
from src.socmint.release_pipeline import release_pipeline_summary
from src.socmint.release_pipeline import release_workflow_spec


def test_release_pipeline_check_shape(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "docker-compose.yml").write_text("services: {}\n")
    (tmp_path / "scripts" / "production_smoke.sh").write_text("#!/usr/bin/env bash\n")
    (tmp_path / "scripts" / "backup_restore_smoke.sh").write_text(
        "#!/usr/bin/env bash\n"
    )

    report = release_pipeline_check(tmp_path)

    assert report["schema"] == "socmint.release_pipeline.v9_3_0"
    assert report["status"] == "ready"
    assert report["checks"]["compose_file_present"] is True
    assert report["checks"]["production_smoke_known"] is True


def test_release_pipeline_summary_counts_checks(tmp_path):
    report = release_pipeline_summary(tmp_path)

    assert report["schema"] == "socmint.release_pipeline.v9_3_0"
    assert report["total_checks"] >= report["passed_checks"]
    assert "docker compose config" in report["required_release_checks"]


def test_release_workflow_spec_documents_artifacts():
    spec = release_workflow_spec()

    assert spec["schema"] == "socmint.release_pipeline.v9_3_0"
    assert "make ci" in spec["manual_release_steps"]
    assert "release readiness JSON" in spec["artifacts"]
