from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .distribution_actions import distribution_action_markdown
from .distribution_actions import distribution_action_packet
from .distribution_actions import distribution_action_summary_path
from .distribution_actions import distribution_action_log_path
from .dossier_certification_index import certification_index_entry
from .dossier_export_store import DEFAULT_EXPORT_ROOT
from .dossier_export_store import load_export_manifest
from .dossier_export_store import safe_slug

DISTRIBUTION_PACKET_EXPORT_SCHEMA = "socmint.distribution_packet_export.v10_15_0"
DISTRIBUTION_PACKET_EXPORT_ROOT = Path("exports") / "distribution_packets"


def _packet_dir(
    case_id: str, subject_id: str, root: str | Path = DISTRIBUTION_PACKET_EXPORT_ROOT
) -> Path:
    return Path(root) / safe_slug(case_id, "case") / safe_slug(subject_id, "subject")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _safe_arcname(path: Path, prefix: str) -> str:
    return f"{prefix}/{safe_slug(path.name, 'artifact')}"


def _manifest_source_path(manifest: dict[str, Any]) -> Path | None:
    manifest_path = manifest.get("manifest_path")
    if manifest_path:
        return Path(str(manifest_path))
    directory = manifest.get("directory")
    if directory:
        return Path(str(directory)) / "manifest.json"
    return None


def build_distribution_packet_export(
    case_id: str,
    subject_id: str,
    export_root: str | Path = DEFAULT_EXPORT_ROOT,
    packet_root: str | Path = DISTRIBUTION_PACKET_EXPORT_ROOT,
    require_approval: bool = True,
) -> dict[str, Any]:
    packet = distribution_action_packet(case_id=case_id, subject_id=subject_id)
    certification = certification_index_entry(
        case_id=case_id, subject_id=subject_id, root=export_root
    )
    manifest = load_export_manifest(
        subject_id=subject_id, case_id=case_id, root=export_root
    )

    if require_approval and not packet.get("distribution_ready"):
        raise ValueError(
            "Cannot build distribution export until the packet is certified and approved."
        )

    out_dir = _packet_dir(case_id, subject_id, root=packet_root)
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / "distribution_packet.zip"
    manifest_path = out_dir / "distribution_export_manifest.json"
    statement_path = out_dir / "distribution_statement.md"
    packet_json_path = out_dir / "distribution_packet.json"

    statement = distribution_action_markdown(case_id=case_id, subject_id=subject_id)
    statement_path.write_text(statement, encoding="utf-8")
    _write_json(packet_json_path, packet)

    action_log = distribution_action_log_path(case_id=case_id, subject_id=subject_id)
    action_summary = distribution_action_summary_path(
        case_id=case_id, subject_id=subject_id
    )

    files: list[dict[str, Any]] = []
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(
            "README.txt",
            f"SOCMINT distribution packet\ncase_id={case_id}\nsubject_id={subject_id}\n",
        )
        archive.write(statement_path, "distribution_statement.md")
        archive.write(packet_json_path, "distribution_packet.json")

        if manifest.get("status") != "missing":
            source_manifest = _manifest_source_path(manifest)
            if source_manifest and source_manifest.exists():
                archive.write(source_manifest, "dossier_manifest.json")
                files.append(
                    {
                        "role": "dossier_manifest",
                        "path": str(source_manifest),
                        "arcname": "dossier_manifest.json",
                        "sha256": _sha256_file(source_manifest),
                    }
                )

        if action_log.exists():
            archive.write(action_log, "operator_action_log.jsonl")
            files.append(
                {
                    "role": "operator_action_log",
                    "path": str(action_log),
                    "arcname": "operator_action_log.jsonl",
                    "sha256": _sha256_file(action_log),
                }
            )
        if action_summary.exists():
            archive.write(action_summary, "operator_action_summary.json")
            files.append(
                {
                    "role": "operator_action_summary",
                    "path": str(action_summary),
                    "arcname": "operator_action_summary.json",
                    "sha256": _sha256_file(action_summary),
                }
            )

        for artifact in manifest.get("artifacts", []):
            artifact_path = Path(str(artifact.get("path", "")))
            if not artifact_path.exists():
                continue
            arcname = _safe_arcname(artifact_path, "artifacts")
            archive.write(artifact_path, arcname)
            files.append(
                {
                    "role": "dossier_artifact",
                    "format": artifact.get("format"),
                    "filename": artifact.get("filename"),
                    "path": str(artifact_path),
                    "arcname": arcname,
                    "sha256": _sha256_file(artifact_path),
                }
            )

    export_manifest = {
        "schema": DISTRIBUTION_PACKET_EXPORT_SCHEMA,
        "status": "ready",
        "case_id": case_id,
        "subject_id": subject_id,
        "distribution_ready": bool(packet.get("distribution_ready")),
        "certification_status": certification.get("certification_status"),
        "safe_to_distribute": certification.get("safe_to_distribute"),
        "recommended_bundle": packet.get("recommended_bundle"),
        "zip_path": str(zip_path),
        "zip_sha256": _sha256_file(zip_path),
        "zip_size_bytes": zip_path.stat().st_size,
        "manifest_path": str(manifest_path),
        "file_count": len(files) + 3,
        "files": files,
    }
    _write_json(manifest_path, export_manifest)
    return export_manifest


def distribution_packet_export_summary(
    case_id: str,
    subject_id: str,
    packet_root: str | Path = DISTRIBUTION_PACKET_EXPORT_ROOT,
) -> dict[str, Any]:
    manifest_path = (
        _packet_dir(case_id, subject_id, root=packet_root)
        / "distribution_export_manifest.json"
    )
    if not manifest_path.exists():
        return {
            "schema": DISTRIBUTION_PACKET_EXPORT_SCHEMA,
            "status": "missing",
            "case_id": case_id,
            "subject_id": subject_id,
            "manifest_path": str(manifest_path),
        }
    return json.loads(manifest_path.read_text(encoding="utf-8"))
