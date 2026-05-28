from __future__ import annotations

from typing import Any

from .claim_evidence_ledger_v13 import build_claim_evidence_ledger
from .dossier_readiness_routes_v13 import subject_dossier_readiness
from .full_report_history import full_report_export_history

SCHEMA = "socmint.handoff_status.v13_6"


def row(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def build_handoff_status(subject_id: int) -> dict[str, Any]:
    readiness = subject_dossier_readiness(subject_id)
    ledger = build_claim_evidence_ledger(subject_id)
    history = full_report_export_history(subject_id, limit=10)
    exports = history.get("exports") or []

    rows = []
    readiness_state = readiness.get("state")
    ready_states = {"draft_ready", "final_ready", "exported"}
    rows.append(
        row(
            "readiness",
            "pass" if readiness_state in ready_states else "block",
            str(readiness_state),
        )
    )

    summary = ledger.get("summary") or {}
    total = int(summary.get("claim_count") or 0)
    missing = int(summary.get("missing_evidence") or 0)
    if total == 0:
        rows.append(row("claim_coverage", "warn", "no rows"))
    elif missing:
        rows.append(row("claim_coverage", "warn", f"missing: {missing}"))
    else:
        rows.append(row("claim_coverage", "pass", "covered"))

    rows.append(row("report", "pass" if exports else "block", f"count: {len(exports)}"))
    rows.append(row("verification", "warn", "planned"))

    block_count = sum(1 for item in rows if item["status"] == "block")
    warning_count = sum(1 for item in rows if item["status"] == "warn")
    if block_count:
        state = "blocked"
    elif warning_count:
        state = "draft_ready"
    else:
        state = "ready"

    return {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "state": state,
        "block_count": block_count,
        "warning_count": warning_count,
        "rows": rows,
        "readiness": readiness,
        "ledger_summary": summary,
        "reports": exports,
    }
