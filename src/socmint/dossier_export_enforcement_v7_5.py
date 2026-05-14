from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

EXPORT_ENFORCEMENT_SCHEMA = "socmint.v7_5.dossier_export_enforcement"
ALLOWED_EXPORT_MODES = {"draft", "preview", "final"}


@dataclass(frozen=True)
class ExportDecision:
    schema: str
    generated_at: str
    approved_line: str
    mode: str
    allowed: bool
    status: str
    reason: str
    quality_status: str
    quality_finding_count: int
    final_export_blocked: bool


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _quality_gate(payload: dict[str, Any]) -> dict[str, Any]:
    gate = payload.get("quality_gate") or {}
    return gate if isinstance(gate, dict) else {}


def normalize_export_mode(mode: str | None) -> str:
    value = (mode or "draft").strip().lower()
    return value if value in ALLOWED_EXPORT_MODES else "draft"


def evaluate_dossier_export(payload: dict[str, Any], mode: str | None = "draft") -> dict[str, Any]:
    export_mode = normalize_export_mode(mode)
    gate = _quality_gate(payload)
    quality_status = str(gate.get("status") or "not_checked")
    quality_finding_count = int(gate.get("finding_count") or 0)

    if export_mode == "final" and quality_status == "fail":
        decision = ExportDecision(
            schema=EXPORT_ENFORCEMENT_SCHEMA,
            generated_at=utc_now(),
            approved_line="v7.5",
            mode=export_mode,
            allowed=False,
            status="blocked",
            reason="Final dossier export is blocked because the v7.5 quality gate failed.",
            quality_status=quality_status,
            quality_finding_count=quality_finding_count,
            final_export_blocked=True,
        )
    else:
        reason = "Draft/preview export allowed with quality gate context." if export_mode != "final" else "Final dossier export allowed."
        decision = ExportDecision(
            schema=EXPORT_ENFORCEMENT_SCHEMA,
            generated_at=utc_now(),
            approved_line="v7.5",
            mode=export_mode,
            allowed=True,
            status="allowed",
            reason=reason,
            quality_status=quality_status,
            quality_finding_count=quality_finding_count,
            final_export_blocked=False,
        )
    return asdict(decision)


def attach_export_enforcement(payload: dict[str, Any], mode: str | None = "draft") -> dict[str, Any]:
    enriched = dict(payload)
    enriched["export_enforcement"] = evaluate_dossier_export(payload, mode=mode)
    enriched["final_export_allowed"] = bool(enriched["export_enforcement"]["allowed"])
    return enriched


def export_block_message(decision: dict[str, Any]) -> str:
    findings = decision.get("quality_finding_count", 0)
    return (
        "Final dossier export blocked by v7.5 quality gate. "
        f"Resolve {findings} missing source/evidence/confidence finding(s), "
        "or use draft/preview mode for analyst review."
    )
