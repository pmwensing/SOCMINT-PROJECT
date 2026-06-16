from pathlib import Path
from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import register_dossier_assembly_routes_v21_0


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v25_5_history_routes_and_ui(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_routes_v25_0 as routes
    payload = {
        "schema":"socmint.cross_case_intelligence_history_audit.v25_5","version":"v25.5.0","status":"ready","generated_at":"2026-06-16T08:00:00+00:00",
        "access_scope":{"mode":"restricted","allowed_case_ids":["case-alpha","case-bravo"]},
        "history":[{"history_event_id":"audit-1","event_type":"analyst_decision","occurred_at":"2026-06-16T06:00:00+00:00","actor":"reviewer-one","correlation_id":"correlation-1","confirmed_link_id":None,"case_ids":["case-alpha","case-bravo"],"source_action":"cross_case_correlation_candidate_review","source_record_id":1,"source_binding_sha256":"a"*64}],
        "event_count":1,"event_type_counts":{"analyst_decision":1},"actor_counts":{"reviewer-one":1},"correlation_count":1,"confirmed_link_count":0,"case_count":2,"source_bound_event_count":1,
        "current_cross_case_intelligence_state":{"candidate_discovery":{"status":"ready"},"reviews":{"disposition_counts":{"accept":1}},"confirmed_links":{"count":0},"relationship_graph":{"status":"ready"},"impact_analyses":{"count":0},"access_scope":{"mode":"restricted"}},
        "current_cross_case_intelligence_state_sha256":"c"*64,
        "source_records_mutated":False,"review_history_mutated":False,"confirmed_link_registry_mutated":False,"graph_mutated":False,"impact_records_created":False,"history_record_created":False,"next_action":"review_cross_case_intelligence_history"
    }
    captured=[]
    monkeypatch.setattr(routes,"build_cross_case_intelligence_history_audit",lambda **kwargs: captured.append(kwargs) or payload)
    client=_app(tmp_path,monkeypatch).test_client()
    assert client.get('/api/v1/cross-case-intelligence/history').status_code==401
    with client.session_transaction() as sess:
        sess['user']='analyst'; sess['allowed_case_ids']=['case-alpha','case-bravo']
    ui=client.get('/cross-case-intelligence/history')
    api=client.get('/api/v1/cross-case-intelligence/history')
    assert ui.status_code==200
    assert b'Cross-Case Intelligence History and Audit' in ui.data
    assert b'Current Cross-Case Intelligence State' in ui.data
    assert b'Ordered Cross-Case Intelligence History' in ui.data
    assert b'reviewer-one' in ui.data and b'correlation-1' in ui.data
    assert b'creates no history record' in ui.data
    assert api.status_code==200 and api.get_json()['event_count']==1
    assert all(item['allowed_case_ids']=={'case-alpha','case-bravo'} for item in captured)


def test_v25_5_release_note_and_no_migration():
    note=Path('release/V25_5_CROSS_CASE_INTELLIGENCE_HISTORY_AUDIT.md').read_text(encoding='utf-8')
    migrations=[p for d in (Path('migrations'),Path('alembic')) if d.exists() for p in d.rglob('*v25_5*')]
    for phrase in ('candidate discovery','analyst decisions','confirmed-link registrations','graph projections','impact analyses','one ordered history','actor','source bindings','access scope','event counts','current cross-case intelligence state','read-only'):
        assert phrase in note
    assert migrations==[]
