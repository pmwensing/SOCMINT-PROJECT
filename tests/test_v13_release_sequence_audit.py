from pathlib import Path
import re


def test_v13_test_backed_gap_release_notes_exist():
    expected = [
        "release/V13_23_WORKFLOW_NAVIGATION.md",
        "release/V13_25_RESERVED_GAP.md",
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

    assert "| v13.25 | Reserved gap |" in audit
    assert "| v13.11 | Documented |" in audit
    assert "| v13.23 | Documented |" in audit
    assert "| v13.27-v13.31 | Documented |" in audit


def test_v13_11_release_note_records_form_payload_fallback():
    note = Path("release/V13_11_NORMALIZATION_FORM_UPDATE.md").read_text()
    source = Path("src/socmint/normalization_review_update_routes_v13.py").read_text()

    assert "normalization_update_payload" in note
    assert "request.form" in note
    assert "normalization_update_payload" in source
    assert "request.form" in source


def test_v13_25_reserved_gap_note_requires_evidence_before_backfill():
    note = Path("release/V13_25_RESERVED_GAP.md").read_text()

    assert "Reserved gap" in note
    assert "No direct `test_v13_25*` regression file is present." in note
    assert "Do not backfill this slot without concrete implementation evidence" in note


def test_v13_numbered_release_sequence_is_accounted_for():
    release_numbers = set()
    for path in Path("release").glob("V13_*"):
        match = re.match(r"V13_(\d+)(?:_|$)", path.name)
        if match:
            release_numbers.add(int(match.group(1)))

    expected = set(range(0, 49))
    missing = sorted(expected - release_numbers)

    assert missing == []


def test_v13_release_documentation_closure_points_to_audit_and_indexes():
    closure = Path("release/V13_RELEASE_DOCUMENTATION_CLOSURE.md").read_text()

    assert "V13_RELEASE_SEQUENCE_AUDIT.md" in closure
    assert "V13_35_FINAL_CORRELATION_SCOPE_CLOSURE.md" in closure
    assert "V13_36_TO_44_EXPORT_BLOCKER_INDEX.md" in closure
    assert "V13_45_TO_48_EXPORT_BLOCKER_WORKFLOW_INDEX.md" in closure
    assert "V13_25_RESERVED_GAP.md" in closure
