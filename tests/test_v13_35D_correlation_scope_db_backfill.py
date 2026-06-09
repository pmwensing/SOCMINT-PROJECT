import sqlite3

from src.socmint import database as db
from src.socmint.correlation_scope_db_backfill_v13_35 import (
    backfill_correlation_scopes,
    db_scope_proof_payload,
    register_correlation_scope_db_backfill_routes_v13_35,
    two_initial_search_db_isolation_proof,
)


def _sqlite_tmp(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint-v13-35d.db'}", create_schema=True)


def test_v13_35d_models_have_correlation_scope_columns():
    for model in [
        db.SpineSeed,
        db.SpineConnectorRun,
        db.SpineObservation,
        db.SpineDossierAssertion,
    ]:
        assert hasattr(model, "correlation_scope_id")
        assert hasattr(model, "correlation_scope_state")
        assert hasattr(model, "correlation_scope_reason")


def test_v13_35d_existing_db_gets_scope_columns_when_auto_create_disabled(tmp_path):
    db_path = tmp_path / "existing-spine.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE spine_subjects (id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE spine_seeds ("
            "id INTEGER PRIMARY KEY, "
            "subject_id INTEGER NOT NULL, "
            "seed_type VARCHAR NOT NULL, "
            "raw_value TEXT NOT NULL, "
            "normalized_value TEXT NOT NULL, "
            "pii_hash VARCHAR NOT NULL"
            ")"
        )

    db.configure_database(f"sqlite:///{db_path}", create_schema=False)

    columns = {column["name"] for column in db.inspect(db.engine).get_columns("spine_seeds")}
    assert "correlation_scope_id" in columns
    assert "correlation_scope_state" in columns
    assert "correlation_scope_reason" in columns


def test_v13_35d_db_backfill_is_idempotent(tmp_path):
    _sqlite_tmp(tmp_path)

    with db.Session() as session:
        subject = db.SpineSubject(label="Scope Subject")
        session.add(subject)
        session.flush()
        seed_a = db.SpineSeed(
            subject_id=subject.id,
            seed_type="username",
            raw_value="alexsmith",
            normalized_value="alexsmith",
            pii_hash="hash-a",
        )
        seed_b = db.SpineSeed(
            subject_id=subject.id,
            seed_type="username",
            raw_value="alexsmith",
            normalized_value="alexsmith",
            pii_hash="hash-b",
        )
        session.add_all([seed_a, seed_b])
        session.commit()

    first = backfill_correlation_scopes()
    second = backfill_correlation_scopes()

    assert first["total_seen"] >= 2
    assert first["total_changed"] >= 2
    assert second["total_changed"] == 0

    proof = db_scope_proof_payload()
    assert proof["schema"] == "socmint.correlation_scope_db_backfill.v13_35D"
    assert proof["tables"]["spine_seeds"]["scoped_count"] >= 2


def test_v13_35d_two_initial_searches_remain_isolated_in_db(tmp_path):
    _sqlite_tmp(tmp_path)

    with db.Session() as session:
        subject = db.SpineSubject(label="Alex Smith")
        session.add(subject)
        session.flush()
        seed_a = db.SpineSeed(
            subject_id=subject.id,
            seed_type="username",
            raw_value="alexsmith",
            normalized_value="alexsmith",
            pii_hash="hash-a",
        )
        seed_b = db.SpineSeed(
            subject_id=subject.id,
            seed_type="username",
            raw_value="alexsmith",
            normalized_value="alexsmith",
            pii_hash="hash-b",
        )
        session.add_all([seed_a, seed_b])
        session.commit()

    backfill_correlation_scopes()

    with db.Session() as session:
        seeds = session.query(db.SpineSeed).order_by(db.SpineSeed.id).all()
        assert len(seeds) == 2
        assert seeds[0].correlation_scope_id
        assert seeds[1].correlation_scope_id
        assert seeds[0].correlation_scope_id != seeds[1].correlation_scope_id


def test_v13_35d_quarantine_first_proof():
    proof = two_initial_search_db_isolation_proof()

    assert proof["schema"] == "socmint.correlation_scope_db_backfill.v13_35D"
    assert proof["separate"] is True
    assert proof["decision"]["state"] == "quarantine"
    assert proof["decision"]["reason"] == "ambiguous_cross_scope_profile"


def test_v13_35d_db_proof_route(tmp_path):
    _sqlite_tmp(tmp_path)

    from src.socmint.wsgi import app

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["is_admin"] = True
        sess["role"] = "admin"

    resp = client.get("/api/v1/audit/correlation-scope/v13.35/db-proof")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["schema"] == "socmint.correlation_scope_db_backfill.v13_35D"
    assert payload["quarantine_first"] is True


def test_v13_35d_routes_are_auth_guarded_and_idempotent(tmp_path):
    _sqlite_tmp(tmp_path)

    from src.socmint.wsgi import app

    register_correlation_scope_db_backfill_routes_v13_35(app)
    register_correlation_scope_db_backfill_routes_v13_35(app)

    client = app.test_client()
    assert client.get("/api/v1/audit/correlation-scope/v13.35/db-proof").status_code == 302

    with client.session_transaction() as sess:
        sess["user"] = "viewer"
        sess["is_admin"] = False
        sess["role"] = "viewer"
        sess["_csrf_token"] = "test-csrf-token"

    assert (
        client.post(
            "/api/v1/admin/correlation-scope/v13.35/backfill",
            headers={"X-CSRF-Token": "test-csrf-token"},
        ).status_code
        == 403
    )
