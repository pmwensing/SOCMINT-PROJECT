import json
from pathlib import Path

import pytest

from src.socmint.dossier_export_gate import export_gate_decision
from src.socmint.dossier_export_store import persist_export_pack
from src.socmint.dossier_export_verification import verify_artifact_hashes
from src.socmint.dossier_export_verification import verify_manifest_index


def _subject(subject_id="subject-scope-136", case_id="case-scope-136"):
    return {
        "subject_id": subject_id,
        "display_name": "Scoped Export Subject",
        "case_id": case_id,
        "aliases": ["scoped-export"],
    }


def _evidence():
    return [
        {
            "evidence_id": "ev-scope-1",
            "label": "scoped profile artifact",
            "source": "public_profile",
            "confidence": 0.96,
            "artifact_id": "art-scope-1",
        }
    ]


def test_export_persist_rejects_requested_case_mismatch(tmp_path):
    with pytest.raises(ValueError, match="outside the requested case scope"):
        persist_export_pack(
            _subject(case_id="case-alpha"),
            _evidence(),
            analyst_reviewed=True,
            root=tmp_path,
            expected_case_id="case-beta",
        )


def test_export_persist_rejects_requested_subject_mismatch(tmp_path):
    with pytest.raises(ValueError, match="outside the requested subject scope"):
        persist_export_pack(
            _subject(subject_id="subject-alpha"),
            _evidence(),
            analyst_reviewed=True,
            root=tmp_path,
            expected_subject_id="subject-beta",
        )


def test_export_verification_blocks_manifest_case_tampering(tmp_path):
    persisted = persist_export_pack(
        _subject(),
        _evidence(),
        analyst_reviewed=True,
        root=tmp_path,
        audit=True,
        expected_subject_id="subject-scope-136",
        expected_case_id="case-scope-136",
    )
    manifest_path = Path(persisted["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["case_id"] = "case-other"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    hashes = verify_artifact_hashes(
        "subject-scope-136", "case-scope-136", root=tmp_path
    )
    index = verify_manifest_index("subject-scope-136", "case-scope-136", root=tmp_path)
    decision = export_gate_decision(
        "subject-scope-136", "case-scope-136", root=tmp_path
    )

    assert hashes["status"] == "blocked"
    assert hashes["scope"]["checks"]["case_match"] is False
    assert index["status"] == "needs_review"
    assert index["checks"]["manifest_scope"] is False
    assert decision["decision"] == "deny"


def test_export_verification_allows_matching_scope(tmp_path):
    persist_export_pack(
        _subject(),
        _evidence(),
        analyst_reviewed=True,
        root=tmp_path,
        audit=True,
        expected_subject_id="subject-scope-136",
        expected_case_id="case-scope-136",
    )

    hashes = verify_artifact_hashes(
        "subject-scope-136", "case-scope-136", root=tmp_path
    )
    index = verify_manifest_index("subject-scope-136", "case-scope-136", root=tmp_path)
    decision = export_gate_decision(
        "subject-scope-136", "case-scope-136", root=tmp_path
    )

    assert hashes["status"] == "pass"
    assert index["status"] == "pass"
    assert decision["decision"] == "allow"
