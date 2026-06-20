from src.socmint.dossier_export_audit import audit_summary
from src.socmint.dossier_export_audit import read_audit_events
from src.socmint.dossier_export_index import resolve_export_download_path
from src.socmint.dossier_export_store import load_export_manifest
from src.socmint.dossier_export_store import persist_export_pack


def _subject():
    return {
        "subject_id": "subject-hooks-108",
        "display_name": "Audit Hook Subject",
        "case_id": "case-hooks-108",
        "aliases": ["audit-hooks"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-hooks-1",
            "label": "hooked profile artifact",
            "source": "public_profile",
            "confidence": 0.95,
            "artifact_id": "art-hooks-1",
        },
        {
            "evidence_id": "ev-hooks-2",
            "label": "hooked registry artifact",
            "source": "public_registry",
            "confidence": 0.9,
            "artifact_id": "art-hooks-2",
        },
    ]


def test_v10_8_persist_export_pack_auto_writes_export_created_audit(tmp_path):
    result = persist_export_pack(
        _subject(),
        _evidence(),
        analyst_reviewed=True,
        root=tmp_path,
        actor="tester",
        audit=True,
    )
    events = read_audit_events("case-hooks-108", "subject-hooks-108", root=tmp_path)

    assert result["audit_event"]["action"] == "export_created"
    assert result["audit_event"]["actor"] == "tester"
    assert len(events) == 1
    assert events[0]["detail"]["artifact_count"] == 2


def test_v10_8_load_export_manifest_can_auto_write_manifest_read_audit(tmp_path):
    persist_export_pack(
        _subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=False
    )
    manifest = load_export_manifest(
        "subject-hooks-108",
        "case-hooks-108",
        root=tmp_path,
        actor="reader",
        audit=True,
    )
    events = read_audit_events("case-hooks-108", "subject-hooks-108", root=tmp_path)

    assert manifest["audit_event"]["action"] == "manifest_read"
    assert manifest["audit_event"]["actor"] == "reader"
    assert len(events) == 1


def test_v10_8_resolve_download_ready_auto_writes_download_resolved_audit(tmp_path):
    persist_export_pack(
        _subject(), _evidence(), analyst_reviewed=True, root=tmp_path, audit=False
    )
    resolved = resolve_export_download_path(
        "case-hooks-108",
        "subject-hooks-108",
        "dossier.html",
        root=tmp_path,
        actor="downloader",
        audit=True,
    )
    summary = audit_summary("case-hooks-108", "subject-hooks-108", root=tmp_path)

    assert resolved["status"] == "ready"
    assert resolved["audit_event"]["action"] == "download_resolved"
    assert resolved["audit_event"]["actor"] == "downloader"
    assert summary["counts"]["download_resolved"] == 1


def test_v10_8_resolve_download_blocked_auto_writes_download_blocked_audit(tmp_path):
    resolved = resolve_export_download_path(
        "case-hooks-108",
        "subject-hooks-108",
        "../../secret.txt",
        root=tmp_path,
        actor="block-test",
        audit=True,
    )
    summary = audit_summary("case-hooks-108", "subject-hooks-108", root=tmp_path)

    assert resolved["status"] == "blocked"
    assert resolved["audit_event"]["action"] == "download_blocked"
    assert summary["counts"]["download_blocked"] == 1


def test_v10_8_resolve_download_missing_auto_writes_download_missing_audit(tmp_path):
    resolved = resolve_export_download_path(
        "case-hooks-108",
        "subject-hooks-108",
        "dossier.html",
        root=tmp_path,
        actor="missing-test",
        audit=True,
    )
    summary = audit_summary("case-hooks-108", "subject-hooks-108", root=tmp_path)

    assert resolved["status"] == "missing"
    assert resolved["audit_event"]["action"] == "download_missing"
    assert summary["counts"]["download_missing"] == 1
