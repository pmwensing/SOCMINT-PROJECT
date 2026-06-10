from pathlib import Path


def test_v13_test_backed_gap_release_notes_exist():
    expected = [
        "release/V13_23_WORKFLOW_NAVIGATION.md",
        "release/V13_27_FULL_REPORT_HISTORY_RUNTIME_SAFE.md",
        "release/V13_28_RUNTIME_ROUTE_HARDENING.md",
        "release/V13_29_FULL_DOSSIER_ENDPOINT_ALIAS.md",
        "release/V13_30_RUNTIME_VISUAL_POLISH.md",
        "release/V13_31_EXPORT_ARTIFACT_UX.md",
    ]

    missing = [path for path in expected if not Path(path).exists()]

    assert missing == []


def test_v13_release_sequence_audit_marks_remaining_true_gaps():
    audit = Path("release/V13_RELEASE_SEQUENCE_AUDIT.md").read_text()

    assert "| v13.11 | Gap |" in audit
    assert "| v13.25 | Gap |" in audit
    assert "| v13.23 | Documented |" in audit
    assert "| v13.27-v13.31 | Documented |" in audit
