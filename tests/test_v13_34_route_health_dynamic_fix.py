from pathlib import Path


def test_support_bundle_dynamic_route_health_fix_is_installed():
    wsgi = Path("src/socmint/wsgi.py").read_text()
    fix = Path("src/socmint/support_bundle_route_health_fix_v13_34.py").read_text()

    assert "install_support_bundle_route_health_fix_v13_34" in wsgi
    assert "route_health_summary_with_dynamic_paths" in fix
    assert "adapter.match(route, method=\"GET\")" in fix
    assert "registered_method_mismatch" in fix


def test_support_bundle_dynamic_route_health_resolves_known_routes():
    from src.socmint.wsgi import app
    from src.socmint.support_bundle_v13_34 import route_health_summary

    rows = route_health_summary(app)
    by_route = {row["route"]: row for row in rows}

    for route in [
        "/command-center",
        "/review/normalization-queue",
        "/subjects/4/dossier/readiness",
        "/subjects/4/claim-evidence-ledger",
        "/spine/subjects/4/dossier",
        "/spine/subjects/4/full-report/history",
        "/spine/subjects/4/full-report/view",
        "/spine/subjects/4/full-report/retention",
        "/release/final-rc/v13.33",
        "/api/v1/dossier-builder/v3/export-blockers/screenshot-manifest",
        "/dossier/export-blockers/screenshot-manifest/download",
    ]:
        assert by_route[route]["registered"] is True, route
        assert by_route[route]["endpoint"], route
