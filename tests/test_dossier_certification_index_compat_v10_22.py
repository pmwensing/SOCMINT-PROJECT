from src.socmint.wsgi import app


def test_v10_22_certification_index_canonical_routes_remain_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/certification-index/<case_id>" in routes
    assert "/api/v1/dossier-builder/v3/certification-index/<case_id>/summary" in routes
    assert "/api/v1/dossier-builder/v3/certification-index/<case_id>/markdown" in routes
    assert "/api/v1/dossier-builder/v3/certification-index/<case_id>/<subject_id>" in routes


def test_v10_22_export_certification_index_compat_routes_are_registered():
    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/v1/dossier-builder/v3/export-certification-index/<case_id>" in routes
    assert "/api/v1/dossier-builder/v3/export-certification-index/<case_id>/summary" in routes
    assert "/api/v1/dossier-builder/v3/export-certification-index/<case_id>/review" in routes


def test_v10_22_compat_routes_are_aliases_not_replacements():
    canonical = []
    compat = []
    for rule in app.url_map.iter_rules():
        if "/api/v1/dossier-builder/v3/certification-index/" in rule.rule:
            canonical.append(rule.rule)
        if "/api/v1/dossier-builder/v3/export-certification-index/" in rule.rule:
            compat.append(rule.rule)

    assert len(canonical) >= 4
    assert len(compat) == 3
