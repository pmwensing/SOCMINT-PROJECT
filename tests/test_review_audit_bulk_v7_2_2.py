from sqlalchemy import inspect

from socmint import database as db
from socmint.report_review import (
    bulk_set_review_status,
    review_audit_payload,
    review_decision_audit_table_available,
    set_review_status,
)


def test_review_decision_audit_model_registered():
    assert "review_decision_audit" in db.Base.metadata.tables


def test_review_decision_audit_create_all(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "review-audit.db"
    url = f"sqlite:///{sqlite_path}"

    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SOCMINT_DATABASE_URL", url)

    db.configure_database(url, create_schema=True)

    tables = set(inspect(db.engine).get_table_names())
    assert "review_decision_audit" in tables


def test_single_decision_writes_audit(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "review-audit-single.db"
    url = f"sqlite:///{sqlite_path}"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SOCMINT_DATABASE_URL", url)

    db.configure_database(url, create_schema=True)

    result = set_review_status(
        "findings:100",
        "approved",
        "single audit",
        reviewer="tester",
    )

    assert result["updated"] is True
    assert result["status"] == "approved"

    if review_decision_audit_table_available():
        payload = review_audit_payload(item_id="findings:100")
        assert payload["items"]


def test_bulk_decisions_write_batch(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "review-audit-bulk.db"
    url = f"sqlite:///{sqlite_path}"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("SOCMINT_DATABASE_URL", url)

    db.configure_database(url, create_schema=True)

    result = bulk_set_review_status(
        ["findings:201", "findings:202"],
        "uncertain",
        "bulk audit",
        reviewer="tester",
    )

    assert result["schema"] == "socmint.bulk_review_decision.v7_2_2"
    assert result["requested"] == 2
    assert result["updated"] == 2
    assert result["batch_id"]

    payload = review_audit_payload(batch_id=result["batch_id"])
    if review_decision_audit_table_available():
        assert len(payload["items"]) == 2
