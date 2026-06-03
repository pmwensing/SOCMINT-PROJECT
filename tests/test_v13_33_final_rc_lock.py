from pathlib import Path


def test_final_rc_routes_registered_in_wsgi():
    wsgi = Path("src/socmint/wsgi.py").read_text()
    assert "register_final_rc_routes_v13_33" in wsgi
    assert "from .final_rc_routes_v13_33 import register_final_rc_routes_v13_33" in wsgi


def test_final_rc_status_route_payload_and_labels():
    source = Path("src/socmint/final_rc_routes_v13_33.py").read_text()

    assert "RC_VERSION = \"v13.33\"" in source
    assert "release_candidate_locked" in source
    assert "/release/final-rc/v13.33" in source
    assert "/api/v1/release/final-rc/v13.33" in source
    for label in [
        "Command Center",
        "Route Acceptance Lock",
        "Export Artifact Acceptance Lock",
        "ZIP",
        "Manifest",
        "HTML",
        "Markdown",
        "JSON",
    ]:
        assert label in source or label.lower().replace(" ", "-") in source


def test_v13_33_acceptance_scripts_committed():
    clean = Path("scripts/clean_install_acceptance_v13_33.sh").read_text()
    runtime = Path("scripts/runtime_acceptance_v13_33.sh").read_text()
    capture = Path("scripts/capture_runtime_pages_v13_33.py").read_text()

    assert "git clone" in clean
    assert "docker compose build --no-cache app" in clean
    assert "runtime_acceptance_v13_33.sh" in clean
    assert "v13.33 Final RC runtime acceptance" in runtime
    assert "export_full_entity_dossier_v2" in runtime
    assert "final_rc_status_payload" in runtime
    assert "SOCMINT_CAPTURE_PASSWORD" in capture
    assert "/release/final-rc/v13.33" in capture


def test_v13_33_release_note_documents_acceptance_lock():
    note = Path("release/V13_33_FINAL_RC_LOCK.md").read_text()

    assert "v13.33" in note
    assert "Final Release Candidate Lock" in note
    assert "Clean clone/build/run acceptance" in note
    assert "Controlled Full Report export artifacts" in note
