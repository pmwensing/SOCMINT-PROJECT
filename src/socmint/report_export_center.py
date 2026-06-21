from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .report_review import list_enrichment_review_items
from .report_review import report_runs_payload
from .report_review import review_summary


ALLOWED_GATE_MODES = {
    "approved_only",
    "approved_and_uncertain",
    "exclude_rejected",
    "all_reviewed",
}


@dataclass
class GatedExport:
    export_id: str
    subject_id: int | None
    gate_mode: str
    status: str
    manifest_path: str
    included_count: int
    excluded_count: int
    generated_at: str


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def export_root() -> Path:
    root = Path("var/socmint/review_gated_exports")
    root.mkdir(parents=True, exist_ok=True)
    return root


def item_allowed(status: str, gate_mode: str) -> bool:
    if gate_mode == "approved_only":
        return status == "approved"

    if gate_mode == "approved_and_uncertain":
        return status in {"approved", "uncertain"}

    if gate_mode == "exclude_rejected":
        return status != "rejected"

    if gate_mode == "all_reviewed":
        return status in {"approved", "rejected", "uncertain"}

    raise ValueError(f"Invalid review gate mode: {gate_mode}")


def build_review_gated_manifest(
    subject_id: int | None = None,
    gate_mode: str = "approved_and_uncertain",
    title: str | None = None,
) -> dict[str, Any]:
    if gate_mode not in ALLOWED_GATE_MODES:
        raise ValueError(f"Invalid review gate mode: {gate_mode}")

    generated_at = utc_now()
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    subject_part = str(subject_id) if subject_id is not None else "all"
    export_id = f"review-gated-{subject_part}-{stamp}"

    items = list_enrichment_review_items(subject_id=subject_id, limit=10000)
    included = []
    excluded = []

    for item in items:
        payload = asdict(item)
        if item_allowed(item.status, gate_mode):
            included.append(payload)
        else:
            excluded.append(payload)

    manifest = {
        "schema": "socmint.review_gated_export_manifest.v7_3",
        "export_id": export_id,
        "title": title or "Review-gated dossier export",
        "subject_id": subject_id,
        "gate_mode": gate_mode,
        "generated_at": generated_at,
        "included_count": len(included),
        "excluded_count": len(excluded),
        "included_items": included,
        "excluded_items": excluded,
        "review_summary": review_summary(),
        "source_report_runs": report_runs_payload(subject_id=subject_id).get(
            "reports",
            [],
        ),
        "policy": {
            "approved_only": "Include only analyst-approved items.",
            "approved_and_uncertain": (
                "Include approved and uncertain items; exclude rejected and "
                "needs-review items."
            ),
            "exclude_rejected": "Include everything except rejected items.",
            "all_reviewed": "Include approved, rejected, and uncertain decisions.",
        }.get(gate_mode),
    }

    manifest_path = export_root() / f"{export_id}-MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    summary_path = export_root() / f"{export_id}-SUMMARY.md"
    summary_path.write_text(render_export_summary(manifest))

    manifest["manifest_path"] = str(manifest_path)
    manifest["summary_path"] = str(summary_path)
    return manifest


def render_export_summary(manifest: dict[str, Any]) -> str:
    lines = [
        f"# {manifest.get('title', 'Review-gated dossier export')}",
        "",
        f"- Export ID: `{manifest.get('export_id')}`",
        f"- Subject ID: `{manifest.get('subject_id')}`",
        f"- Gate mode: `{manifest.get('gate_mode')}`",
        f"- Generated: `{manifest.get('generated_at')}`",
        f"- Included items: `{manifest.get('included_count')}`",
        f"- Excluded items: `{manifest.get('excluded_count')}`",
        "",
        "## Review gate policy",
        "",
        str(manifest.get("policy") or ""),
        "",
        "## Included items",
        "",
    ]

    included = manifest.get("included_items") or []
    if not included:
        lines.append("_No included items._")
    else:
        for item in included:
            lines.extend(
                [
                    f"### {item.get('id')}",
                    "",
                    f"- Status: `{item.get('status')}`",
                    f"- Quality: `{item.get('quality')}`",
                    f"- Confidence: `{item.get('confidence')}`",
                    f"- Source: `{item.get('source')}`",
                    f"- Label: `{item.get('label')}`",
                    "",
                    "```text",
                    str(item.get("value") or ""),
                    "```",
                    "",
                ]
            )

    lines.extend(["", "## Excluded items", ""])

    excluded = manifest.get("excluded_items") or []
    if not excluded:
        lines.append("_No excluded items._")
    else:
        for item in excluded:
            lines.append(f"- `{item.get('id')}` — status `{item.get('status')}`")

    return "\n".join(lines).rstrip() + "\n"


def list_review_gated_exports(limit: int = 100) -> list[GatedExport]:
    root = export_root()
    manifests = sorted(
        root.glob("review-gated-*-MANIFEST.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    exports: list[GatedExport] = []
    for path in manifests[:limit]:
        try:
            payload = json.loads(path.read_text(errors="replace"))
        except json.JSONDecodeError:
            payload = {}

        exports.append(
            GatedExport(
                export_id=str(payload.get("export_id") or path.stem),
                subject_id=payload.get("subject_id"),
                gate_mode=str(payload.get("gate_mode") or "unknown"),
                status="complete",
                manifest_path=str(path),
                included_count=int(payload.get("included_count") or 0),
                excluded_count=int(payload.get("excluded_count") or 0),
                generated_at=str(payload.get("generated_at") or ""),
            )
        )

    return exports


def review_gated_export_payload(
    subject_id: int | None = None,
    gate_mode: str = "approved_and_uncertain",
    title: str | None = None,
) -> dict[str, Any]:
    manifest = build_review_gated_manifest(
        subject_id=subject_id,
        gate_mode=gate_mode,
        title=title,
    )
    return {
        "schema": "socmint.review_gated_export_result.v7_3",
        "generated_at": utc_now(),
        "manifest": manifest,
    }


def safe_export_artifact_path(relative_or_name: str) -> Path:
    root = export_root().resolve()
    candidate = Path(relative_or_name)

    if candidate.is_absolute():
        path = candidate.resolve()
    else:
        path = (root / candidate).resolve()

    if root not in path.parents and path != root:
        raise ValueError("Export artifact path escapes export root")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))

    return path


def export_artifact_metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "download_url": f"/reports/export-center/artifacts/{path.name}/download",
        "view_url": f"/reports/export-center/manifests/{path.name}",
    }


def list_export_artifacts(limit: int = 200) -> list[dict[str, Any]]:
    root = export_root()
    artifacts = sorted(
        [
            p
            for p in root.glob("review-gated-*")
            if p.is_file() and p.suffix.lower() in {".json", ".md", ".txt"}
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [export_artifact_metadata(path) for path in artifacts[:limit]]


def load_manifest_view(name: str) -> dict[str, Any]:
    path = safe_export_artifact_path(name)
    text = path.read_text(errors="replace")

    parsed = None
    if path.suffix.lower() == ".json":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None

    return {
        "schema": "socmint.export_artifact_view.v7_3_1",
        "artifact": export_artifact_metadata(path),
        "is_json": path.suffix.lower() == ".json",
        "is_markdown": path.suffix.lower() == ".md",
        "parsed": parsed,
        "text": text,
    }


def export_center_payload() -> dict[str, Any]:
    return {
        "schema": "socmint.report_export_center.v7_3_1",
        "generated_at": utc_now(),
        "gate_modes": sorted(ALLOWED_GATE_MODES),
        "review_summary": review_summary(),
        "exports": [asdict(item) for item in list_review_gated_exports()],
        "artifacts": list_export_artifacts(),
        "bundles": list_export_bundles(),
    }


def bundle_root() -> Path:
    root = export_root() / "bundles"
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_export_bundle_path(name: str) -> Path:
    root = bundle_root().resolve()
    path = (root / Path(name).name).resolve()

    if root not in path.parents and path != root:
        raise ValueError("Bundle path escapes bundle root")

    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))

    return path


def bundle_metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        "download_url": f"/reports/export-center/bundles/{path.name}/download",
    }


def list_export_bundles(limit: int = 100) -> list[dict[str, Any]]:
    bundles = sorted(
        [p for p in bundle_root().glob("*.zip") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [bundle_metadata(path) for path in bundles[:limit]]


def _bundle_manifest_paths(manifest: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []

    for key in ("manifest_path", "summary_path"):
        value = manifest.get(key)
        if value:
            try:
                paths.append(safe_export_artifact_path(str(value)))
            except (FileNotFoundError, ValueError):
                pass

    export_id = manifest.get("export_id")
    if export_id:
        for path in export_root().glob(f"{export_id}-*"):
            if path.is_file() and path not in paths:
                paths.append(path)

    return paths


def build_export_zip_bundle(
    subject_id: int | None = None,
    gate_mode: str = "approved_and_uncertain",
    title: str | None = None,
    include_audit: bool = True,
) -> dict[str, Any]:
    manifest = build_review_gated_manifest(
        subject_id=subject_id,
        gate_mode=gate_mode,
        title=title,
    )

    export_id = str(manifest["export_id"])
    zip_path = bundle_root() / f"{export_id}-BUNDLE.zip"

    included_paths = _bundle_manifest_paths(manifest)

    audit_payload = {
        "schema": "socmint.export_bundle_audit_snapshot.v7_3_2",
        "generated_at": utc_now(),
        "export_id": export_id,
        "subject_id": subject_id,
        "gate_mode": gate_mode,
        "review_summary": manifest.get("review_summary"),
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in included_paths:
            zf.write(path, arcname=path.name)

        zf.writestr(
            f"{export_id}-AUDIT-SNAPSHOT.json",
            json.dumps(audit_payload, indent=2, sort_keys=True),
        )

        zf.writestr(
            "README.txt",
            "\n".join(
                [
                    "SOCMINT Review-Gated Export Bundle",
                    f"Export ID: {export_id}",
                    f"Gate mode: {gate_mode}",
                    f"Included items: {manifest.get('included_count')}",
                    f"Excluded items: {manifest.get('excluded_count')}",
                    "",
                    "This ZIP was generated by v7.3.2.",
                ]
            ),
        )

    result = {
        "schema": "socmint.export_zip_bundle.v7_3_2",
        "generated_at": utc_now(),
        "export_id": export_id,
        "subject_id": subject_id,
        "gate_mode": gate_mode,
        "bundle": bundle_metadata(zip_path),
        "manifest_path": manifest.get("manifest_path"),
        "summary_path": manifest.get("summary_path"),
        "included_count": manifest.get("included_count"),
        "excluded_count": manifest.get("excluded_count"),
        "artifact_count": len(included_paths),
        "include_audit": include_audit,
    }

    bundle_manifest_path = export_root() / f"{export_id}-BUNDLE-MANIFEST.json"
    bundle_manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    result["bundle_manifest_path"] = str(bundle_manifest_path)

    return result


def export_zip_bundle_payload(
    subject_id: int | None = None,
    gate_mode: str = "approved_and_uncertain",
    title: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "socmint.export_zip_bundle_result.v7_3_2",
        "generated_at": utc_now(),
        "result": build_export_zip_bundle(
            subject_id=subject_id,
            gate_mode=gate_mode,
            title=title,
        ),
    }
