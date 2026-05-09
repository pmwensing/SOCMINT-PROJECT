from pathlib import Path

from sqlalchemy import inspect

from socmint import database as db
from socmint.report_review import (
    review_decision_table_available,
    set_review_status,
)


def test_review_decisions_model_registered():
    assert "review_decisions" in db.Base.metadata.tables


def test_review_decisions_create_all(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "review-decisions.db"
    url = f"sqlite:///{sqlite_path}"

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SOCMINT_DATABASE_URL", url)

    db.configure_database(url, create_schema=True)

    tables = set(inspect(db.engine).get_table_names())
    assert "review_decisions" in tables


def test_set_review_status_persists_or_sidecars(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "review-decisions-write.db"
    url = f"sqlite:///{sqlite_path}"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SOCMINT_DATABASE_URL", url)

    db.configure_database(url, create_schema=True)

    result = set_review_status("findings:999", "approved", "confirmed")

    assert result["updated"] is True
    assert result["status"] == "approved"

    if review_decision_table_available():
        assert result.get("native") is True
        assert result.get("decision_id") is not None
    else:
        assert result.get("sidecar") is True
        assert Path(result["path"]).exists()
