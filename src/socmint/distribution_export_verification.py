from __future__ import annotations

import hashlib
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from .distribution_packet_export import DISTRIBUTION_PACKET_EXPORT_ROOT
from .distribution_packet_export import DISTRIBUTION_PACKET_EXPORT_SCHEMA
from .distribution_packet_export import distribution_packet_export_summary

DISTRIBUTION_EXPORT_VERIFICATION_SCHEMA = "socmint.distribution_export_verification.v10_16_0"
REQUIRED_ZIP_FILES = {
    "README.txt",
    "distribution_statement.md",
    "distribution_packet.json",
    "dossier_manifest.json",
    "operator_action_log.jsonl",
    "operator_action_summary.json",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_status(zip_path: Path, manifest: dict) -> dict:
    try:
        with ZipFile(zip_path) as archive:
            names = set(archive.namelist())
    except BadZipFile:
        return {"status": "fail", "zip_files": [], "required_missing": sorted(REQUIRED_ZIP_FILES), "artifact_files": [], "expected_artifact_count": 0, "actual_artifact_count": 0, "blockers": ["bad_zip"]}
    blockers = []
    missing = sorted(REQUIRED_ZIP_FILES - names)
    if missing:
        blockers.append("required_files_missing")
    artifact_files = sorted(name for name in names if name.startswith("artifacts/"))
    expected = [item for item in manifest.get("files", []) if item.get("role") == "dossier_artifact"]
    if len(artifact_files) != len(expected):
        blockers.append("artifact_count_mismatch")
    return {"status": "pass" if not blockers else "fail", "zip_files": sorted(names), "required_missing": missing, "artifact_files": artifact_files, "expected_artifact_count": len(expected), "actual_artifact_count": len(artifact_files), "blockers": blockers}


def verify_distribution_export(case_id: str, subject_id: str, packet_root: str | Path = DISTRIBUTION_PACKET_EXPORT_ROOT) -> dict:
    manifest = distribution_packet_export_summary(case_id=case_id, subject_id=subject_id, packet_root=packet_root)
    if manifest.get("status") == "missing":
        return {"schema": DISTRIBUTION_EXPORT_VERIFICATION_SCHEMA, "status": "missing", "case_id": case_id, "subject_id": subject_id, "verified": False, "blockers": ["missing_distribution_export_manifest"], "manifest": manifest}

    blockers = []
    if manifest.get("schema") != DISTRIBUTION_PACKET_EXPORT_SCHEMA:
        blockers.append("unexpected_export_schema")
    if not manifest.get("distribution_ready"):
        blockers.append("distribution_not_ready")

    zip_path = Path(str(manifest.get("zip_path", "")))
    if not zip_path.exists():
        blockers.append("zip_missing")
        zip_info = {"status": "missing", "zip_files": [], "required_missing": sorted(REQUIRED_ZIP_FILES), "artifact_files": [], "expected_artifact_count": 0, "actual_artifact_count": 0, "blockers": ["zip_missing"]}
    else:
        if _sha256_file(zip_path) != manifest.get("zip_sha256"):
            blockers.append("zip_hash_mismatch")
        if zip_path.stat().st_size != manifest.get("zip_size_bytes"):
            blockers.append("zip_size_mismatch")
        zip_info = _zip_status(zip_path, manifest)
        blockers.extend(zip_info.get("blockers", []))

    file_checks = []
    for item in manifest.get("files", []):
        source_path = Path(str(item.get("path", "")))
        exists = source_path.exists()
        actual = _sha256_file(source_path) if exists else None
        expected = item.get("sha256")
        ok = bool(exists and actual == expected)
        if not exists:
            blockers.append("source_file_missing")
        elif actual != expected:
            blockers.append("source_file_hash_mismatch")
        file_checks.append({"role": item.get("role"), "arcname": item.get("arcname"), "path": str(source_path), "exists": exists, "expected_sha256": expected, "actual_sha256": actual, "verified": ok})

    blockers = sorted(set(blockers))
    return {"schema": DISTRIBUTION_EXPORT_VERIFICATION_SCHEMA, "status": "pass" if not blockers else "fail", "case_id": case_id, "subject_id": subject_id, "verified": not blockers, "blockers": blockers, "zip_status": zip_info, "file_checks": file_checks, "manifest": manifest}


def distribution_export_verification_markdown(case_id: str, subject_id: str, packet_root: str | Path = DISTRIBUTION_PACKET_EXPORT_ROOT) -> str:
    result = verify_distribution_export(case_id=case_id, subject_id=subject_id, packet_root=packet_root)
    lines = [f"# Distribution Export Verification — {case_id} / {subject_id}", "", f"Status: {result.get('status')}", f"Verified: {result.get('verified')}", f"Blockers: {', '.join(result.get('blockers', [])) or 'none'}", "", "## File checks"]
    for item in result.get("file_checks", []):
        lines.append(f"- {item.get('role')} — {item.get('arcname')} — verified={item.get('verified')}")
    if not result.get("file_checks"):
        lines.append("- No files checked.")
    return "\n".join(lines) + "\n"
