from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .report_export_center import bundle_root
from .report_export_center import export_root
from .report_export_center import safe_export_artifact_path


ALLOWED_EVIDENCE_SUFFIXES = {
    ".csv",
    ".doc",
    ".docx",
    ".eml",
    ".html",
    ".jpeg",
    ".jpg",
    ".json",
    ".md",
    ".msg",
    ".pdf",
    ".png",
    ".txt",
    ".webp",
    ".xlsx",
    ".zip",
}


@dataclass
class EvidenceArtifact:
    evidence_id: str
    case_id: str | None
    subject_id: int | None
    original_name: str
    stored_name: str
    path: str
    sha256: str
    size_bytes: int
    mime_type: str
    intake_status: str
    created_at: str
    source_note: str | None = None


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def evidence_root() -> Path:
    root = Path("var/socmint/evidence")
    root.mkdir(parents=True, exist_ok=True)
    return root


def evidence_manifest_path() -> Path:
    return evidence_root() / "EVIDENCE-MANIFEST.json"


def _load_manifest() -> list[dict[str, Any]]:
    path = evidence_manifest_path()
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(errors="replace"))
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        return list(data.get("items") or [])

    if isinstance(data, list):
        return data

    return []


def _write_manifest(items: list[dict[str, Any]]) -> None:
    payload = {
        "schema": "socmint.evidence_manifest.v7_4",
        "generated_at": utc_now(),
        "count": len(items),
        "items": items,
    }
    evidence_manifest_path().write_text(json.dumps(payload, indent=2, sort_keys=True))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_filename(name: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "_"
        for char in Path(name).name
    ).strip("._")

    return cleaned or "evidence.bin"


def safe_evidence_path(name: str) -> Path:
    root = evidence_root().resolve()
    path = (root / Path(name).name).resolve()

    if root not in path.parents and path != root:
        raise ValueError("Evidence path escapes evidence root")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))

    return path


def intake_evidence_file(
    source_path: str | Path,
    case_id: str | None = None,
    subject_id: int | None = None,
    source_note: str | None = None,
) -> dict[str, Any]:
    src = Path(source_path).expanduser().resolve()

    if not src.exists() or not src.is_file():
        raise FileNotFoundError(str(src))

    suffix = src.suffix.lower()
    if suffix and suffix not in ALLOWED_EVIDENCE_SUFFIXES:
        raise ValueError(f"Unsupported evidence file type: {suffix}")

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    original = safe_filename(src.name)
    stored_name = f"{stamp}_{original}"
    dest = evidence_root() / stored_name

    shutil.copy2(src, dest)

    digest = sha256_file(dest)
    mime_type = mimetypes.guess_type(dest.name)[0] or "application/octet-stream"

    artifact = EvidenceArtifact(
        evidence_id=digest[:16],
        case_id=case_id,
        subject_id=subject_id,
        original_name=src.name,
        stored_name=stored_name,
        path=str(dest),
        sha256=digest,
        size_bytes=dest.stat().st_size,
        mime_type=mime_type,
        intake_status="stored",
        created_at=utc_now(),
        source_note=source_note,
    )

    items = _load_manifest()

    if not any(item.get("sha256") == digest for item in items):
        items.append(asdict(artifact))
        _write_manifest(items)

    from .evidence_custody import record_custody_event

    record_custody_event(
        evidence_id=artifact.evidence_id,
        action="intake",
        actor=None,
        sha256=artifact.sha256,
        status="stored",
        note=source_note,
        details={
            "case_id": case_id,
            "subject_id": subject_id,
            "stored_name": stored_name,
            "original_name": src.name,
        },
    )

    return asdict(artifact)


def list_evidence(
    case_id: str | None = None,
    subject_id: int | None = None,
) -> list[dict[str, Any]]:
    items = _load_manifest()

    if case_id:
        items = [item for item in items if item.get("case_id") == case_id]

    if subject_id is not None:
        items = [item for item in items if item.get("subject_id") == subject_id]

    return items


def evidence_intake_payload(
    case_id: str | None = None,
    subject_id: int | None = None,
) -> dict[str, Any]:
    items = list_evidence(case_id=case_id, subject_id=subject_id)

    return {
        "schema": "socmint.evidence_intake.v7_4",
        "generated_at": utc_now(),
        "case_id": case_id,
        "subject_id": subject_id,
        "count": len(items),
        "items": items,
    }


def attachment_manifest_for_export(
    export_manifest_name: str,
    case_id: str | None = None,
    subject_id: int | None = None,
) -> dict[str, Any]:
    export_manifest_path = safe_export_artifact_path(export_manifest_name)
    export_manifest = json.loads(export_manifest_path.read_text(errors="replace"))

    evidence_items = list_evidence(case_id=case_id, subject_id=subject_id)

    try:
        from .evidence_links import linked_evidence_for_export_manifest

        linked_items = linked_evidence_for_export_manifest(export_manifest_name)
    except Exception:
        linked_items = []

    by_sha = {item.get("sha256"): item for item in evidence_items if item.get("sha256")}
    for item in linked_items:
        sha = item.get("sha256")
        if sha and sha not in by_sha:
            evidence_items.append(item)
            by_sha[sha] = item

    attached = []
    missing = []

    for item in evidence_items:
        path = Path(str(item.get("path", "")))
        if path.exists() and path.is_file():
            attached.append(item)
        else:
            missing.append(item)

    payload = {
        "schema": "socmint.export_attachment_manifest.v7_4",
        "generated_at": utc_now(),
        "export_manifest": str(export_manifest_path),
        "export_id": export_manifest.get("export_id"),
        "case_id": case_id,
        "subject_id": subject_id,
        "attachment_count": len(attached),
        "missing_count": len(missing),
        "attachments": attached,
        "missing": missing,
        "review_gate": export_manifest.get("gate_mode"),
    }

    out = export_root() / f"{export_manifest.get('export_id')}-ATTACHMENTS.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True))
    payload["attachment_manifest_path"] = str(out)

    return payload


def build_attachment_zip(
    export_manifest_name: str,
    case_id: str | None = None,
    subject_id: int | None = None,
) -> dict[str, Any]:
    attach_manifest = attachment_manifest_for_export(
        export_manifest_name=export_manifest_name,
        case_id=case_id,
        subject_id=subject_id,
    )

    export_id = str(attach_manifest.get("export_id") or "export")
    zip_path = bundle_root() / f"{export_id}-EVIDENCE-ATTACHMENTS.zip"

    import zipfile

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest_path = Path(str(attach_manifest["attachment_manifest_path"]))
        zf.write(manifest_path, arcname=manifest_path.name)

        for item in attach_manifest.get("attachments") or []:
            path = Path(str(item.get("path", "")))
            if path.exists() and path.is_file():
                zf.write(path, arcname=f"evidence/{item.get('stored_name')}")
                from .evidence_custody import record_custody_event

                record_custody_event(
                    evidence_id=str(item.get("evidence_id")),
                    action="export_attach",
                    actor=None,
                    sha256=item.get("sha256"),
                    status="attached",
                    note="included in export attachment ZIP",
                    details={
                        "export_id": export_id,
                        "zip_path": str(zip_path),
                        "stored_name": item.get("stored_name"),
                    },
                )

        zf.writestr(
            "README.txt",
            "\n".join(
                [
                    "SOCMINT Evidence Attachment Bundle",
                    f"Export ID: {export_id}",
                    f"Case ID: {case_id}",
                    f"Subject ID: {subject_id}",
                    f"Attachment count: {attach_manifest.get('attachment_count')}",
                    "",
                    (
                        "Each evidence file is listed in the attachment "
                        "manifest with SHA-256."
                    ),
                ]
            ),
        )

    result = {
        "schema": "socmint.export_attachment_zip.v7_4",
        "generated_at": utc_now(),
        "export_id": export_id,
        "case_id": case_id,
        "subject_id": subject_id,
        "zip_path": str(zip_path),
        "download_url": (f"/reports/export-center/bundles/{zip_path.name}/download"),
        "attachment_manifest_path": attach_manifest["attachment_manifest_path"],
        "attachment_count": attach_manifest["attachment_count"],
        "missing_count": attach_manifest["missing_count"],
    }

    return result
