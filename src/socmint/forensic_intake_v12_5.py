from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "socmint.forensic_intake.v12_5"
MANIFEST_SCHEMA = "socmint.forensic_preservation_manifest.v12_5"
CUSTODY_SCHEMA = "socmint.chain_of_custody.v12_5"

DROPZONE_NAMES = [
    "images",
    "video",
    "audio",
    "documents",
    "chat_exports",
    "email_exports",
    "social_exports",
    "device_dumps",
    "metadata_only",
    "quarantine",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".csv", ".xls", ".xlsx", ".ppt", ".pptx"}
CHAT_EXTENSIONS = {".json", ".html", ".htm", ".xml"}
EMAIL_EXTENSIONS = {".eml", ".mbox", ".msg", ".pst"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def data_root(root: str | None = None) -> Path:
    return Path(root or os.environ.get("SOCMINT_DATA_DIR", "var/socmint"))


def forensic_root(root: str | None = None) -> Path:
    return data_root(root) / "forensic_intake"


def dropzones_root(root: str | None = None) -> Path:
    return forensic_root(root) / "dropzones"


def vault_root(root: str | None = None) -> Path:
    return forensic_root(root) / "vault"


def manifests_root(root: str | None = None) -> Path:
    return forensic_root(root) / "manifests"


def ensure_dropzones(root: str | None = None) -> dict[str, Any]:
    base = dropzones_root(root)
    paths = {}
    for name in DROPZONE_NAMES:
        path = base / name
        path.mkdir(parents=True, exist_ok=True)
        paths[name] = str(path)
    vault_root(root).mkdir(parents=True, exist_ok=True)
    manifests_root(root).mkdir(parents=True, exist_ok=True)
    return {"schema": SCHEMA, "created_at": utc_now(), "dropzones": paths, "vault": str(vault_root(root)), "manifests": str(manifests_root(root))}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    if ext in EMAIL_EXTENSIONS:
        return "email_export"
    if ext in CHAT_EXTENSIONS:
        return "chat_or_structured_export"
    return "unknown"


def preservation_subdir(kind: str) -> str:
    return kind if kind in {"image", "video", "audio", "document", "email_export", "chat_or_structured_export"} else "unknown"


def probe_tool(name: str) -> bool:
    return shutil.which(name) is not None


def safe_subprocess(command: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return {"available": True, "command": command, "returncode": result.returncode, "stdout": result.stdout[:8000], "stderr": result.stderr[:4000]}
    except FileNotFoundError:
        return {"available": False, "command": command, "error": "tool not installed"}
    except subprocess.TimeoutExpired as exc:
        return {"available": True, "command": command, "error": "timeout", "stdout": (exc.stdout or "")[:8000], "stderr": (exc.stderr or "")[:4000]}


def extract_metadata(path: Path, kind: str) -> dict[str, Any]:
    stat = path.stat()
    mime, encoding = mimetypes.guess_type(str(path))
    metadata: dict[str, Any] = {
        "filename": path.name,
        "extension": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "ctime": datetime.fromtimestamp(stat.st_ctime, UTC).isoformat(),
        "mime_guess": mime,
        "encoding_guess": encoding,
        "kind": kind,
    }
    if kind in {"image", "video", "audio", "document"} and probe_tool("exiftool"):
        metadata["exiftool"] = safe_subprocess(["exiftool", "-json", str(path)], timeout=30)
    if kind in {"video", "audio"} and probe_tool("ffprobe"):
        metadata["ffprobe"] = safe_subprocess(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)], timeout=30)
    return metadata


def analysis_hooks(path: Path, kind: str) -> dict[str, Any]:
    hooks: dict[str, Any] = {"ocr": {"status": "not_applicable"}, "transcription": {"status": "not_applicable"}}
    if kind in {"image", "document"}:
        hooks["ocr"] = {"status": "available" if probe_tool("tesseract") else "not_installed", "tool": "tesseract", "note": "v12.5 records OCR readiness; full OCR extraction is enabled when tesseract is installed."}
    if kind in {"video", "audio"}:
        hooks["transcription"] = {"status": "available" if (probe_tool("whisper") or probe_tool("whisperx")) else "not_installed", "tool": "whisper/whisperx", "note": "v12.5 records transcription readiness; full transcript generation is enabled when speech tooling is installed."}
    if kind == "video":
        hooks["frame_extraction"] = {"status": "available" if probe_tool("ffmpeg") else "not_installed", "tool": "ffmpeg"}
    return hooks


@dataclass
class CustodyEvent:
    timestamp: str
    action: str
    actor: str
    file_sha256: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreservedEvidence:
    evidence_id: str
    original_path: str
    preserved_path: str
    original_sha256: str
    preserved_sha256: str
    size_bytes: int
    kind: str
    mime_type: str | None
    ingested_at: str
    custody: list[CustodyEvent]
    metadata: dict[str, Any]
    analysis: dict[str, Any]
    court_safe: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        item = asdict(self)
        item["custody"] = [asdict(event) if hasattr(event, "__dataclass_fields__") else event for event in self.custody]
        return item


def preserve_file(path: Path, actor: str = "system", root: str | None = None, source: str = "dropzone") -> PreservedEvidence:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    original_sha = sha256_file(path)
    kind = file_kind(path)
    evidence_id = original_sha[:16]
    target_dir = vault_root(root) / preservation_subdir(kind) / evidence_id
    target_dir.mkdir(parents=True, exist_ok=True)
    preserved_path = target_dir / f"original{path.suffix.lower()}"
    if not preserved_path.exists():
        shutil.copy2(path, preserved_path)
    preserved_sha = sha256_file(preserved_path)
    metadata = extract_metadata(preserved_path, kind)
    analysis = analysis_hooks(preserved_path, kind)
    mime, _ = mimetypes.guess_type(str(path))
    custody = [
        CustodyEvent(utc_now(), "hash_original", actor, original_sha, {"source_path": str(path), "source": source}),
        CustodyEvent(utc_now(), "preserve_original_copy", actor, preserved_sha, {"preserved_path": str(preserved_path)}),
        CustodyEvent(utc_now(), "verify_preserved_hash", actor, preserved_sha, {"verified": preserved_sha == original_sha}),
    ]
    return PreservedEvidence(
        evidence_id=evidence_id,
        original_path=str(path),
        preserved_path=str(preserved_path),
        original_sha256=original_sha,
        preserved_sha256=preserved_sha,
        size_bytes=preserved_path.stat().st_size,
        kind=kind,
        mime_type=mime,
        ingested_at=utc_now(),
        custody=custody,
        metadata=metadata,
        analysis=analysis,
        court_safe={
            "immutable_original_preserved": True,
            "hash_verified": preserved_sha == original_sha,
            "working_copy_required_for_analysis": True,
            "evidence_grade": preserved_sha == original_sha,
            "note": "Original preserved before analysis. Derivatives must reference this evidence_id and sha256.",
        },
    )


def _iter_intake_files(root: str | None = None) -> list[Path]:
    base = dropzones_root(root)
    if not base.exists():
        ensure_dropzones(root)
    files = []
    for path in base.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            files.append(path)
    return sorted(files)


def write_manifest(items: list[PreservedEvidence], root: str | None = None) -> dict[str, Any]:
    out = manifests_root(root)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    manifest_path = out / f"forensic_preservation_manifest_{stamp}.json"
    custody_path = out / f"chain_of_custody_{stamp}.json"
    csv_path = out / f"forensic_preservation_manifest_{stamp}.csv"
    payload = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": utc_now(),
        "item_count": len(items),
        "items": [item.as_dict() for item in items],
        "court_safe_summary": {
            "hash_verified": sum(1 for item in items if item.court_safe.get("hash_verified")),
            "immutable_originals": sum(1 for item in items if item.court_safe.get("immutable_original_preserved")),
            "evidence_grade": sum(1 for item in items if item.court_safe.get("evidence_grade")),
        },
    }
    custody = {
        "schema": CUSTODY_SCHEMA,
        "generated_at": utc_now(),
        "events": [asdict(event) for item in items for event in item.custody],
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    custody_path.write_text(json.dumps(custody, indent=2, sort_keys=True))
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["evidence_id", "kind", "mime_type", "size_bytes", "original_sha256", "preserved_sha256", "preserved_path", "hash_verified"])
        writer.writeheader()
        for item in items:
            writer.writerow({
                "evidence_id": item.evidence_id,
                "kind": item.kind,
                "mime_type": item.mime_type,
                "size_bytes": item.size_bytes,
                "original_sha256": item.original_sha256,
                "preserved_sha256": item.preserved_sha256,
                "preserved_path": item.preserved_path,
                "hash_verified": item.court_safe.get("hash_verified"),
            })
    return {"manifest": payload, "manifest_path": str(manifest_path), "custody_path": str(custody_path), "csv_path": str(csv_path)}


def ingest_dropzones(actor: str = "system", root: str | None = None) -> dict[str, Any]:
    ensure_dropzones(root)
    items = []
    errors = []
    for path in _iter_intake_files(root):
        if "quarantine" in path.parts:
            continue
        try:
            items.append(preserve_file(path, actor=actor, root=root, source="dropzone"))
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})
    written = write_manifest(items, root=root)
    return {
        "schema": SCHEMA,
        "status": "pass" if not errors else "review",
        "ingested_count": len(items),
        "error_count": len(errors),
        "errors": errors,
        "dropzones": ensure_dropzones(root),
        **written,
    }


def intake_dashboard_payload(root: str | None = None) -> dict[str, Any]:
    ensure_dropzones(root)
    pending = _iter_intake_files(root)
    latest_manifest = None
    manifests = sorted(manifests_root(root).glob("forensic_preservation_manifest_*.json")) if manifests_root(root).exists() else []
    if manifests:
        try:
            latest_manifest = json.loads(manifests[-1].read_text())
        except Exception:
            latest_manifest = None
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "dropzones": ensure_dropzones(root),
        "pending_count": len(pending),
        "pending_files": [{"path": str(path), "kind": file_kind(path), "size_bytes": path.stat().st_size} for path in pending[:100]],
        "latest_manifest": latest_manifest,
        "tool_readiness": {
            "exiftool": probe_tool("exiftool"),
            "ffmpeg": probe_tool("ffmpeg"),
            "ffprobe": probe_tool("ffprobe"),
            "tesseract": probe_tool("tesseract"),
            "whisper": probe_tool("whisper") or probe_tool("whisperx"),
        },
        "court_safe_rules": [
            "Hash before processing.",
            "Preserve immutable original copy.",
            "Analyze derivatives only.",
            "Every promotion must reference evidence_id and sha256.",
            "Manifest and chain-of-custody required for court-safe export.",
        ],
    }
