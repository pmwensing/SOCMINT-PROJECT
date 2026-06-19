from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v29-0-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v29_0_routes_require_admin_and_render_workspace(tmp_path, monkeypatch):
    from src.socmint import collection_operations_routes_v29_0 as routes
    payload = {
        "schema":"socmint.collection_operations_workspace.v29_0",
        "version":"v29.0.0",
        "status":"ready",
        "collection_inventory":[],
        "collection_run_count":0,
        "job_inventory":[],
        "job_count":0,
        "job_status_counts":{},
        "connector_status_counts":{},
        "stale_jobs":[],
        "stale_job_count":0,
        "duplicate_run_groups":[],
        "duplicate_run_group_count":0,
        "retry_eligibility":[],
        "retry_eligible_count":0,
        "evidence_summary":{},
        "observation_summary":{},
        "provenance_summary":{},
        "target_bindings":[],
        "optional_spine_tables":{},
        "dossier_value_summary":{},
        "operator_findings":[],
        "operator_finding_count":0,
        "read_only":True,
        "connector_execution_available":False,
        "job_mutation_available":False,
        "retry_execution_available":False,
        "credential_rotation_available":False,
        "secret_values_visible":False,
        "case_access_scope_changed":False,
        "evidence_rewritten":False,
    }
    captured = []
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(routes, "build_collection_operations_workspace", lambda **kwargs: captured.append(kwargs) or payload)
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/collection-operations").status_code == 401
    assert client.get("/collection-operations").status_code in {302,303}
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/collection-operations").status_code == 403
    assert client.get("/collection-operations").status_code == 403
    with client.session_transaction() as sess:
        sess["user"] = "admin"
    ui = client.get("/collection-operations?stale_after_hours=12")
    api = client.get("/api/v1/collection-operations?stale_after_hours=12")
    assert ui.status_code == 200
    assert b"Collection Operations Workspace" in ui.data
    assert b"connector" in ui.data.lower()
    assert api.status_code == 200
    assert api.get_json()["read_only"] is True
    assert captured == [{"stale_after_hours":12},{"stale_after_hours":12}]


def test_v29_0_release_note_and_no_migration():
    note = Path("release/V29_0_COLLECTION_OPERATIONS_WORKSPACE.md").read_text(encoding="utf-8")
    for phrase in (
        "Collection Operations Workspace",
        "read-only aggregation",
        "collection inventory",
        "connector runs",
        "collection jobs",
        "evidence outputs",
        "observation outputs",
        "provenance completeness",
        "retry eligibility",
        "dossier-value contribution",
        "administrator required",
        "no connector execution",
        "no job mutation",
        "no secret exposure",
        "no case-access change",
        "no evidence rewrite",
        "no migration",
    ):
        assert phrase in note
    migrations = [path for directory in (Path("migrations"),Path("alembic")) if directory.exists() for path in directory.rglob("*v29_0*")]
    assert migrations == []
