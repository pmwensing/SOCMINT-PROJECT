from pathlib import Path


GUIDE = Path("release/V13_26_OPERATOR_GUIDE_AND_TEST_SCRIPT.md")


def test_v13_26_operator_guide_exists():
    assert GUIDE.exists()


def test_v13_26_operator_guide_covers_runtime_test_steps():
    text = GUIDE.read_text()

    required = [
        "docker compose build",
        "docker compose up -d",
        "/readyz",
        "/command-center",
        "/review/normalization-queue",
        "/subjects/<subject_id>/dossier/readiness",
        "/subjects/<subject_id>/claim-evidence-ledger",
        "/subjects/<subject_id>/export-manifest",
        "tests/test_v13_21_usability_smoke.py",
        "tests/test_v13_22_release_route_audit.py",
    ]

    missing = [item for item in required if item not in text]
    assert missing == []


def test_v13_26_operator_guide_has_stop_conditions():
    text = GUIDE.read_text()

    assert "Stop conditions" in text
    assert "Container fails to boot" in text
    assert "Any v13 workflow page returns 500" in text
