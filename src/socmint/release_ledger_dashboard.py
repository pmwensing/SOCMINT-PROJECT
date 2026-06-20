from __future__ import annotations

from .distribution_release_ledger import release_ledger_summary
from .distribution_release_ledger import release_state
from .dossier_certification_index import certification_index

RELEASE_LEDGER_DASHBOARD_SCHEMA = "socmint.release_ledger_dashboard.v10_18_0"


def release_ledger_dashboard(case_id: str) -> dict:
    index = certification_index(case_id=case_id)
    ledger = release_ledger_summary(case_id=case_id)
    rows = []
    counts = {"released": 0, "ready_to_seal": 0, "held": 0}
    for entry in index.get("entries", []):
        subject_id = entry.get("subject_id")
        if not subject_id:
            continue
        state = release_state(case_id=case_id, subject_id=subject_id)
        release_status = state.get("release_state", "held")
        counts[release_status] = counts.get(release_status, 0) + 1
        seal = state.get("seal") or {}
        verification = state.get("verification") or {}
        rows.append(
            {
                "case_id": case_id,
                "subject_id": subject_id,
                "release_state": release_status,
                "sealed": state.get("sealed", False),
                "seal_id": seal.get("seal_id"),
                "released_at": seal.get("created_at"),
                "actor": seal.get("actor"),
                "zip_sha256": seal.get("zip_sha256")
                or verification.get("manifest", {}).get("zip_sha256"),
                "zip_path": seal.get("zip_path")
                or verification.get("manifest", {}).get("zip_path"),
                "verification_status": seal.get("verification_status")
                or verification.get("status"),
                "safe_to_distribute": entry.get("safe_to_distribute"),
                "certified": entry.get("certified"),
                "blockers": entry.get("blockers", []),
            }
        )
    return {
        "schema": RELEASE_LEDGER_DASHBOARD_SCHEMA,
        "case_id": case_id,
        "export_count": len(index.get("entries", [])),
        "release_count": ledger.get("release_count", 0),
        "counts": counts,
        "rows": rows,
        "ledger": ledger,
    }


def release_ledger_dashboard_markdown(case_id: str) -> str:
    payload = release_ledger_dashboard(case_id)
    lines = [
        f"# Release Ledger Dashboard — {case_id}",
        "",
        f"Exports: {payload['export_count']}",
        f"Released: {payload['counts'].get('released', 0)}",
        f"Ready to seal: {payload['counts'].get('ready_to_seal', 0)}",
        f"Held: {payload['counts'].get('held', 0)}",
        "",
        "| Subject | State | Seal ID | ZIP SHA-256 | Verification |",
        "|---|---|---|---|---|",
    ]
    for row in payload["rows"]:
        lines.append(
            "| {subject} | {state} | {seal} | {ziphash} | {verification} |".format(
                subject=row.get("subject_id"),
                state=row.get("release_state"),
                seal=row.get("seal_id") or "none",
                ziphash=row.get("zip_sha256") or "none",
                verification=row.get("verification_status") or "unknown",
            )
        )
    return "\n".join(lines) + "\n"
