from pathlib import Path


def test_capture_runtime_pages_includes_export_blocker_pages():
    source = Path("scripts/capture_runtime_pages_v13_33.py").read_text()

    assert "export-blockers-allowed" in source
    assert "export-blockers-denied" in source
    assert "case-export-ok-v13-40" in source
    assert "case-export-held-v13-40" in source


def test_makefile_exposes_export_blocker_screenshot_target():
    source = Path("Makefile").read_text()

    assert "export-blocker-runtime-screenshots" in source
    assert "scripts/create_export_blocker_fixture_v13_40.py" in source
    assert "scripts/capture_runtime_pages_v13_33.py" in source


def test_ci_has_explicit_command_center_export_gate_verification():
    source = Path(".github/workflows/ci.yml").read_text()

    assert "Command Center export gate verification" in source
    assert "tests/test_command_center_export_gate_v13_40.py" in source
    assert "tests/test_export_blocker_routes_v13_39.py" in source
