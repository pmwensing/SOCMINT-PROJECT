from __future__ import annotations

import hashlib
import io
import json
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_handoff_export_bundle_v7_5_8 import HANDOFF_EXPORT_MANIFEST_SCHEMA
from .dossier_finalization_handoff_export_bundle_v7_5_8 import build_handoff_export_bundle_files

HANDOFF_EXPORT_VERIFY_SCHEMA = "socmint.v7_5_9.dossier_finalization_handoff_export_verification"
HANDOFF_EXPORT_VERIFY_SUMMARY_SCHEMA = "socmint.v7_5_9.dossier_finalization_handoff_export_verification.summary"
APPROVED_LINE = "v7.5.9"
VERIFY_VERIFIED = "verified"
VERIFY_REVIEW = "needs_human_review"
VERIFY_FAILED = "failed"

REQUIRED_FILES = (
    "README.md",
    "handoff_index.json",
    "handoff_index.md",
    "handoff_index_summary.json",
    "manifest.json",
)
RECOGNIZED_CONTENT_TYPES = {"application/json", "text/markdown", "text/plain"}

ACTIONS = {
    "invalid_zip": "Regenerate the v7.5.8 handoff export ZIP.",
    "unsafe_zip_path": "Reject the ZIP and regenerate the export with safe relative paths.",
    "missing_required_file": "Regenerate the v7.5.8 handoff export bundle.",
    "invalid_manifest_json": "Regenerate the handoff export manifest.",
    "wrong_manifest_schema": "Regenerate the export with the v7.5.8 manifest schema.",
    "manifest_file_count_mismatch": "Regenerate the export manifest from the bundle files.",
    "manifest_row_missing_file": "Regenerate the export manifest from the bundle files.",
    "sha256_mismatch": "Regenerate the v7.5.8 handoff export bundle.",
    "size_mismatch": "Regenerate the v7.5.8 handoff export bundle.",
    "invalid_handoff_index_json": "Regenerate the handoff index JSON.",
    "invalid_handoff_summary_json": "Regenerate the handoff index summary JSON.",
    "recommended_action_mismatch": "Regenerate the handoff export bundle and review handoff metadata.",
    "verification_status_mismatch": "Regenerate the handoff export bundle and review handoff metadata.",
    "unexpected_file": "Review unexpected files before handoff.",
    "unrecognized_content_type": "Review manifest content types before handoff.",
    "non_archive_ready_handoff": "Complete human review or regenerate the bundle before handoff.",
    "empty_readme": "Regenerate the export README.",
    "empty_handoff_markdown": "Regenerate the handoff Markdown.",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _finding(severity: str, code: str, detail: str, *, path: str | None = None) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "path": path,
        "detail": detail,
        "action": ACTIONS.get(code, "Review this handoff export verification finding before handoff."),
    }


def _safe_zip_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return bool(normalized) and not normalized.startswith("/") and ".." not in normalized.split("/")


def _load_json(files: dict[str, bytes], path: str, failures: list[dict[str, Any]], code: str) -> dict[str, Any]:
    try:
        return json.loads(files[path].decode("utf-8"))
    except Exception:
        failures.append(_finding("fail", code, f"{path} is invalid JSON.", path=path))
        return {}


def summarize_handoff_export_verification(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": HANDOFF_EXPORT_VERIFY_SUMMARY_SCHEMA,
        "status": report.get("status"),
        "verified": bool(report.get("verified")),
        "failure_count": int(report.get("failure_count") or 0),
        "warning_count": int(report.get("warning_count") or 0),
        "recommended_action": report.get("recommended_action"),
        "verification_status": report.get("verification_status"),
        "certificate_status": report.get("certificate_status"),
        "missing_files": list(report.get("missing_files") or []),
        "unexpected_files": list(report.get("unexpected_files") or []),
    }


def _base_report(files: dict[str, bytes]) -> dict[str, Any]:
    present = sorted(files)
    required = list(REQUIRED_FILES)
    return {
        "schema": HANDOFF_EXPORT_VERIFY_SCHEMA,
        "approved_line": APPROVED_LINE,
        "generated_at": utc_now(),
        "status": VERIFY_FAILED,
        "verified": False,
        "failure_count": 0,
        "warning_count": 0,
        "required_files": required,
        "present_files": present,
        "missing_files": sorted(set(required) - set(present)),
        "unexpected_files": sorted(set(present) - set(required)),
        "manifest": {},
        "file_results": [],
        "recommended_action": None,
        "verification_status": None,
        "certificate_status": None,
        "failures": [],
        "warnings": [],
        "summary": {},
    }


def verify_handoff_export_files(files: dict[str, bytes]) -> dict[str, Any]:
    safe_files = {str(path): bytes(data) for path, data in deepcopy(files or {}).items()}
    report = _base_report(safe_files)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    file_results: list[dict[str, Any]] = []

    for path in report["missing_files"]:
        failures.append(_finding("fail", "missing_required_file", "Required file is missing.", path=path))
    for path in report["unexpected_files"]:
        warnings.append(_finding("warn", "unexpected_file", "Unexpected extra file is present.", path=path))

    if "manifest.json" not in safe_files:
        manifest = {}
    else:
        manifest = _load_json(safe_files, "manifest.json", failures, "invalid_manifest_json")
    report["manifest"] = manifest

    if manifest and manifest.get("schema") != HANDOFF_EXPORT_MANIFEST_SCHEMA:
        failures.append(_finding("fail", "wrong_manifest_schema", "Manifest schema does not match v7.5.8 handoff export manifest schema.", path="manifest.json"))

    manifest_files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    if manifest and int(manifest.get("file_count") or -1) != len(safe_files):
        failures.append(_finding("fail", "manifest_file_count_mismatch", "Manifest file count does not match actual file count.", path="manifest.json"))

    for row in manifest_files:
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "")
        content_type = str(row.get("content_type") or "")
        result = {"path": path, "manifest_present": True, "hash_match": False, "size_match": False, "content_type": content_type}
        if path not in safe_files:
            failures.append(_finding("fail", "manifest_row_missing_file", "Manifest row points to a file that is not present.", path=path))
            file_results.append(result)
            continue
        data = safe_files[path]
        if path == "manifest.json":
            result["hash_match"] = True
            result["size_match"] = True
        else:
            result["hash_match"] = sha256_bytes(data) == row.get("sha256")
            result["size_match"] = len(data) == int(row.get("size_bytes") or -1)
            if not result["hash_match"]:
                failures.append(_finding("fail", "sha256_mismatch", "Manifest SHA-256 does not match file bytes.", path=path))
            if not result["size_match"]:
                failures.append(_finding("fail", "size_mismatch", "Manifest size does not match file bytes.", path=path))
        if content_type not in RECOGNIZED_CONTENT_TYPES:
            warnings.append(_finding("warn", "unrecognized_content_type", "Manifest content type is missing or unrecognized.", path=path))
        file_results.append(result)

    handoff_index = _load_json(safe_files, "handoff_index.json", failures, "invalid_handoff_index_json") if "handoff_index.json" in safe_files else {}
    summary = _load_json(safe_files, "handoff_index_summary.json", failures, "invalid_handoff_summary_json") if "handoff_index_summary.json" in safe_files else {}
    report["recommended_action"] = handoff_index.get("recommended_action") if handoff_index else None
    report["verification_status"] = handoff_index.get("verification_status") if handoff_index else None
    report["certificate_status"] = handoff_index.get("certificate_status") if handoff_index else None

    if handoff_index and summary:
        if handoff_index.get("recommended_action") != summary.get("recommended_action"):
            failures.append(_finding("fail", "recommended_action_mismatch", "Handoff summary recommended action differs from handoff index recommended action.", path="handoff_index_summary.json"))
        if handoff_index.get("verification_status") != summary.get("verification_status"):
            failures.append(_finding("fail", "verification_status_mismatch", "Handoff summary verification status differs from handoff index verification status.", path="handoff_index_summary.json"))
        if handoff_index.get("recommended_action") in {"human_review_required", "regenerate_bundle"}:
            warnings.append(_finding("warn", "non_archive_ready_handoff", "Handoff export is structurally intact but not archive-ready.", path="handoff_index.json"))

    if not safe_files.get("README.md", b"").strip():
        warnings.append(_finding("warn", "empty_readme", "README is empty.", path="README.md"))
    if not safe_files.get("handoff_index.md", b"").strip():
        warnings.append(_finding("warn", "empty_handoff_markdown", "Handoff Markdown is empty.", path="handoff_index.md"))

    status = VERIFY_FAILED if failures else VERIFY_REVIEW if warnings else VERIFY_VERIFIED
    report.update(
        {
            "status": status,
            "verified": status == VERIFY_VERIFIED,
            "failure_count": len(failures),
            "warning_count": len(warnings),
            "file_results": file_results,
            "failures": failures,
            "warnings": warnings,
        }
    )
    report["summary"] = summarize_handoff_export_verification(report)
    return report


def verify_handoff_export_zip(zip_bytes: bytes) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            names = archive.namelist()
            unsafe = [name for name in names if not _safe_zip_path(name)]
            files = {name: archive.read(name) for name in names if _safe_zip_path(name)}
    except Exception:
        report = _base_report({})
        report["failures"] = [_finding("fail", "invalid_zip", "ZIP bytes are invalid or cannot be opened.")]
        report["failure_count"] = 1
        report["summary"] = summarize_handoff_export_verification(report)
        return report

    report = verify_handoff_export_files(files)
    if unsafe:
        failures = list(report["failures"])
        for path in unsafe:
            failures.append(_finding("fail", "unsafe_zip_path", "ZIP entry uses an unsafe absolute or traversal path.", path=path))
        report["failures"] = failures
        report["failure_count"] = len(failures)
        report["status"] = VERIFY_FAILED
        report["verified"] = False
        report["summary"] = summarize_handoff_export_verification(report)
    return report


def verify_handoff_export_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    return verify_handoff_export_files(build_handoff_export_bundle_files(deepcopy(bundle or {})))
