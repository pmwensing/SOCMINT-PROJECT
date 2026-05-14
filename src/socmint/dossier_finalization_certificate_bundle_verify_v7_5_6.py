from __future__ import annotations

import hashlib
import io
import json
import zipfile
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .dossier_finalization_certificate_bundle_v7_5_5 import CERTIFICATE_BUNDLE_MANIFEST_SCHEMA
from .dossier_finalization_certificate_bundle_v7_5_5 import build_certificate_bundle_files
from .dossier_finalization_certificate_v7_5_4 import certificate_digest

BUNDLE_VERIFY_SCHEMA = "socmint.v7_5_6.dossier_finalization_certificate_bundle_verification"
BUNDLE_VERIFY_SUMMARY_SCHEMA = "socmint.v7_5_6.dossier_finalization_certificate_bundle_verification.summary"
APPROVED_LINE = "v7.5.6"
VERIFY_VERIFIED = "verified"
VERIFY_REVIEW = "needs_human_review"
VERIFY_FAILED = "failed"

REQUIRED_FILES = (
    "README.md",
    "certificate.json",
    "certificate.md",
    "certificate_summary.json",
    "manifest.json",
)
RECOGNIZED_CONTENT_TYPES = {"application/json", "text/markdown", "text/plain"}

ACTIONS = {
    "invalid_zip": "Regenerate the v7.5.5 certificate bundle ZIP.",
    "unsafe_zip_path": "Reject the ZIP and regenerate the bundle with safe relative paths.",
    "missing_required_file": "Regenerate the v7.5.5 certificate bundle.",
    "invalid_manifest_json": "Regenerate the certificate bundle manifest.",
    "wrong_manifest_schema": "Regenerate the bundle with the v7.5.5 manifest schema.",
    "manifest_file_count_mismatch": "Regenerate the bundle manifest from the bundle files.",
    "manifest_row_missing_file": "Regenerate the bundle manifest from the bundle files.",
    "sha256_mismatch": "Regenerate the v7.5.5 certificate bundle.",
    "size_mismatch": "Regenerate the v7.5.5 certificate bundle.",
    "invalid_certificate_json": "Regenerate the certificate JSON.",
    "invalid_certificate_summary_json": "Regenerate the certificate summary JSON.",
    "certificate_status_mismatch": "Regenerate the certificate bundle and review certificate metadata.",
    "certificate_valid_mismatch": "Regenerate the certificate bundle and review certificate metadata.",
    "certificate_digest_mismatch": "Regenerate the v7.5.4 certificate before bundling.",
    "unexpected_file": "Review unexpected files before handoff.",
    "unrecognized_content_type": "Review manifest content types before handoff.",
    "non_valid_certificate": "Complete human review before handoff.",
    "empty_readme": "Regenerate the bundle README.",
    "empty_certificate_markdown": "Regenerate the certificate Markdown.",
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
        "action": ACTIONS.get(code, "Review this bundle verification finding before handoff."),
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


def summarize_bundle_verification(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": BUNDLE_VERIFY_SUMMARY_SCHEMA,
        "status": report.get("status"),
        "verified": bool(report.get("verified")),
        "failure_count": int(report.get("failure_count") or 0),
        "warning_count": int(report.get("warning_count") or 0),
        "certificate_status": report.get("certificate_status"),
        "certificate_valid": bool(report.get("certificate_valid")),
        "missing_files": list(report.get("missing_files") or []),
        "unexpected_files": list(report.get("unexpected_files") or []),
    }


def _base_report(files: dict[str, bytes]) -> dict[str, Any]:
    present = sorted(files)
    required = list(REQUIRED_FILES)
    return {
        "schema": BUNDLE_VERIFY_SCHEMA,
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
        "certificate_status": None,
        "certificate_valid": False,
        "failures": [],
        "warnings": [],
        "summary": {},
    }


def verify_certificate_bundle_files(files: dict[str, bytes]) -> dict[str, Any]:
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

    if manifest and manifest.get("schema") != CERTIFICATE_BUNDLE_MANIFEST_SCHEMA:
        failures.append(_finding("fail", "wrong_manifest_schema", "Manifest schema does not match v7.5.5 certificate bundle manifest schema.", path="manifest.json"))

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

    certificate = _load_json(safe_files, "certificate.json", failures, "invalid_certificate_json") if "certificate.json" in safe_files else {}
    summary = _load_json(safe_files, "certificate_summary.json", failures, "invalid_certificate_summary_json") if "certificate_summary.json" in safe_files else {}
    report["certificate_status"] = certificate.get("status") if certificate else None
    report["certificate_valid"] = bool(certificate.get("valid")) if certificate else False

    if certificate and summary:
        if certificate.get("status") != summary.get("status"):
            failures.append(_finding("fail", "certificate_status_mismatch", "Certificate summary status differs from certificate status.", path="certificate_summary.json"))
        if bool(certificate.get("valid")) != bool(summary.get("valid")):
            failures.append(_finding("fail", "certificate_valid_mismatch", "Certificate summary validity differs from certificate valid flag.", path="certificate_summary.json"))
        if certificate_digest(certificate) != certificate.get("certificate_sha256"):
            failures.append(_finding("fail", "certificate_digest_mismatch", "Certificate digest does not match certificate_sha256.", path="certificate.json"))
        if certificate.get("status") in {"failed", "needs_human_review"}:
            warnings.append(_finding("warn", "non_valid_certificate", "Certificate bundle is structurally intact but certificate is not valid.", path="certificate.json"))

    if not safe_files.get("README.md", b"").strip():
        warnings.append(_finding("warn", "empty_readme", "README is empty.", path="README.md"))
    if not safe_files.get("certificate.md", b"").strip():
        warnings.append(_finding("warn", "empty_certificate_markdown", "Certificate Markdown is empty.", path="certificate.md"))

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
    report["summary"] = summarize_bundle_verification(report)
    return report


def verify_certificate_bundle_zip(zip_bytes: bytes) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            names = archive.namelist()
            unsafe = [name for name in names if not _safe_zip_path(name)]
            files = {name: archive.read(name) for name in names if _safe_zip_path(name)}
    except Exception:
        report = _base_report({})
        report["failures"] = [_finding("fail", "invalid_zip", "ZIP bytes are invalid or cannot be opened.")]
        report["failure_count"] = 1
        report["summary"] = summarize_bundle_verification(report)
        return report

    report = verify_certificate_bundle_files(files)
    if unsafe:
        failures = list(report["failures"])
        for path in unsafe:
            failures.append(_finding("fail", "unsafe_zip_path", "ZIP entry uses an unsafe absolute or traversal path.", path=path))
        report["failures"] = failures
        report["failure_count"] = len(failures)
        report["status"] = VERIFY_FAILED
        report["verified"] = False
        report["summary"] = summarize_bundle_verification(report)
    return report


def verify_certificate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    return verify_certificate_bundle_files(build_certificate_bundle_files(deepcopy(bundle or {})))
