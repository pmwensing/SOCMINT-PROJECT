import json

from src.socmint.archivebox_adapter import capture_url
from src.socmint.archivebox_adapter import parse_archivebox_output
from src.socmint.spine import create_subject, run_spine_for_subject
from src.socmint import database as db


def test_archivebox_parse_json_output():
    stdout = json.dumps(
        {
            "results": [
                {
                    "url": "https://example.com/profile",
                    "timestamp": "20260507123456",
                    "title": "Example Profile",
                    "index_path": "archive/20260507123456/index.html",
                    "status": "succeeded",
                }
            ]
        }
    )

    parsed = parse_archivebox_output(stdout)

    assert parsed[0]["url"] == "https://example.com/profile"
    assert parsed[0]["timestamp"] == "20260507123456"


def test_archivebox_dry_run_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.delenv("SOCMINT_ARCHIVEBOX_ENABLED", raising=False)

    result = capture_url("https://example.com/profile")

    assert result["status"] == "dry_run"
    assert result["findings"][0]["type"] == "archive_candidate"
    assert result["artifact"]["sha256"]


def test_spine_archivebox_url_seed_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.delenv("SOCMINT_ARCHIVEBOX_ENABLED", raising=False)
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")

    subject_id = create_subject(
        "Archive Subject",
        [{"type": "url", "value": "https://example.com/profile"}],
    )
    result = run_spine_for_subject(subject_id, ["archivebox"])

    observations = db.list_spine_observations(subject_id)

    assert result["run_ids"]
    assert observations
    assert observations[0].observation_type == "archive_candidate"


def test_archivebox_capture_mocked_success(tmp_path, monkeypatch):
    monkeypatch.setenv("SOCMINT_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SOCMINT_ARCHIVEBOX_ENABLED", "1")
    monkeypatch.setattr(
        "src.socmint.archivebox_adapter.archivebox_available",
        lambda: True,
    )

    class Result:
        returncode = 0
        stdout = json.dumps(
            {
                "results": [
                    {
                        "url": "https://example.com/profile",
                        "timestamp": "20260507123456",
                        "index_path": "archive/20260507123456/index.html",
                    }
                ]
            }
        )
        stderr = ""

    monkeypatch.setattr(
        "src.socmint.archivebox_adapter.subprocess.run",
        lambda *args, **kwargs: Result(),
    )

    result = capture_url("https://example.com/profile")

    assert result["status"] == "completed"
    assert result["findings"][0]["type"] == "archive_snapshot"
    assert result["artifact"]["sha256"]
