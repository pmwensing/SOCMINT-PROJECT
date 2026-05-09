
from __future__ import annotations

import json
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
            lines.append(
                f"- `{item.get('id')}` — status `{item.get('status')}`"
            )

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


def export_center_payload() -> dict[str, Any]:
    return {
        "schema": "socmint.report_export_center.v7_3",
        "generated_at": utc_now(),
        "gate_modes": sorted(ALLOWED_GATE_MODES),
        "review_summary": review_summary(),
        "exports": [asdict(item) for item in list_review_gated_exports()],
    }


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
