from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    monkeypatch.setenv("SOCMINT_SECRET_KEY", "v29-3-route-test-secret-key-with-more-than-32-characters")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v29_3_routes_require_admin_and_dispatch(tmp_path, monkeypatch):
    from src.socmint import connector_adapter_routes_v29_3 as routes
    payload = {"status":"ready","adapter_contracts":[],"active_adapter_contracts":[],"adapter_contract_count":0,"active_adapter_contract_count":0,"adapter_summaries":[],"error_class_catalog":[],"conformance_evaluations":[],"conformance_evaluation_count":0,"conformance_counts":{},"adapter_findings":[],"adapter_finding_count":0,"adapter_history":[],"adapter_event_count":0}
    monkeypatch.setattr(routes, "actor_is_administrator", lambda actor: actor == "admin")
    monkeypatch.setattr(routes, "build_connector_adapter_workspace", lambda: payload)
    monkeypatch.setattr(routes, "create_adapter_contract", lambda **kwargs: {"status":"adapter_contract_created","adapter_contract_id":"adapter-1"})
    monkeypatch.setattr(routes, "revise_adapter_contract", lambda *args, **kwargs: {"status":"adapter_contract_revised","adapter_contract_id":"adapter-2"})
    monkeypatch.setattr(routes, "evaluate_adapter_conformance", lambda **kwargs: {"status":"adapter_conformance_evaluated","evaluation":{"conformant":True}})
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/collection-operations/adapters").status_code == 401
    with client.session_transaction() as sess:
        sess["user"] = "viewer"
    assert client.get("/api/v1/collection-operations/adapters").status_code == 403
    csrf = "v29-3-csrf-token"
    with client.session_transaction() as sess:
        sess["user"] = "admin"
        sess["_csrf_token"] = csrf
    headers = {"X-CSRF-Token": csrf}
    assert client.get("/collection-operations/adapters").status_code == 200
    assert client.get("/api/v1/collection-operations/adapters").status_code == 200
    created = client.post("/api/v1/collection-operations/adapters", json={"connector_id":"connector-1","capabilities":["lookup"],"input_schema":{"type":"object"},"output_schema":{"type":"object"},"reason":"define","confirmed":True}, headers=headers)
    revised = client.post("/api/v1/collection-operations/adapters/adapter-1/revise", json={"definition":{"capabilities":["lookup"],"error_classes":[]},"reason":"revise","confirmed":True}, headers=headers)
    evaluated = client.post("/api/v1/collection-operations/adapters/adapter-1/evaluate", json={"observed_capabilities":["lookup"],"observed_input_schema":{"type":"object"},"observed_output_schema":{"type":"object"},"reason":"evaluate","confirmed":True}, headers=headers)
    assert [created.status_code,revised.status_code,evaluated.status_code] == [200,200,200]


def test_v29_3_release_note_and_no_migration():
    note = Path("release/V29_3_CONNECTOR_NORMALIZATION_ADAPTER_CONTRACT.md").read_text(encoding="utf-8")
    for phrase in ("Connector Normalization and Adapter Contract","capability declaration","input schema","output schema","authorization requirements","rate-limit metadata","deterministic error classes","provenance requirements","health contract","dossier-value declaration","conformance evaluation","no connector execution","no secret exposure","no connector added for breadth","no migration"):
        assert phrase in note
    migrations = [path for directory in (Path("migrations"),Path("alembic")) if directory.exists() for path in directory.rglob("*v29_3*")]
    assert migrations == []
