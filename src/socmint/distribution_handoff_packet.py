from __future__ import annotations

from .distribution_export_verification import verify_distribution_export
from .distribution_release_ledger import release_ledger_summary
from .distribution_release_ledger import release_seal_markdown
from .release_ledger_dashboard import release_ledger_dashboard

DISTRIBUTION_HANDOFF_PACKET_SCHEMA = "socmint.distribution_handoff_packet.v10_19_0"


def distribution_handoff_packet(case_id: str) -> dict:
    dashboard = release_ledger_dashboard(case_id=case_id)
    ledger = release_ledger_summary(case_id=case_id)
    subjects = []
    for row in dashboard.get("rows", []):
        subject_id = row.get("subject_id")
        if not subject_id:
            continue
        verification = verify_distribution_export(
            case_id=case_id, subject_id=subject_id
        )
        subjects.append(
            {
                "case_id": case_id,
                "subject_id": subject_id,
                "release_state": row.get("release_state"),
                "sealed": row.get("sealed"),
                "seal_id": row.get("seal_id"),
                "released_at": row.get("released_at"),
                "actor": row.get("actor"),
                "zip_sha256": row.get("zip_sha256"),
                "zip_path": row.get("zip_path"),
                "verification_status": verification.get("status"),
                "verification_blockers": verification.get("blockers", []),
                "verified": verification.get("verified"),
                "download_url": f"/api/v1/dossier-builder/v3/distribution-export/{case_id}/{subject_id}/download",
                "verify_url": f"/api/v1/dossier-builder/v3/distribution-export/{case_id}/{subject_id}/verify",
                "release_state_url": f"/api/v1/dossier-builder/v3/distribution-release/{case_id}/{subject_id}",
                "seal_markdown_url": f"/api/v1/dossier-builder/v3/distribution-release/{case_id}/{subject_id}/markdown",
            }
        )
    counts = dashboard.get("counts", {})
    return {
        "schema": DISTRIBUTION_HANDOFF_PACKET_SCHEMA,
        "case_id": case_id,
        "status": "ready",
        "export_count": dashboard.get("export_count", 0),
        "release_count": ledger.get("release_count", 0),
        "released_count": counts.get("released", 0),
        "ready_to_seal_count": counts.get("ready_to_seal", 0),
        "held_count": counts.get("held", 0),
        "subjects": subjects,
        "ledger": ledger,
    }


def distribution_handoff_markdown(case_id: str) -> str:
    packet = distribution_handoff_packet(case_id=case_id)
    lines = [
        f"# Release Distribution Handoff Packet — {case_id}",
        "",
        f"Exports: {packet['export_count']}",
        f"Released: {packet['released_count']}",
        f"Ready to seal: {packet['ready_to_seal_count']}",
        f"Held: {packet['held_count']}",
        "",
        "| Subject | State | Seal ID | ZIP SHA-256 | Verification |",
        "|---|---|---|---|---|",
    ]
    for subject in packet["subjects"]:
        lines.append(
            "| {subject} | {state} | {seal} | {ziphash} | {verification} |".format(
                subject=subject.get("subject_id"),
                state=subject.get("release_state"),
                seal=subject.get("seal_id") or "none",
                ziphash=subject.get("zip_sha256") or "none",
                verification=subject.get("verification_status") or "unknown",
            )
        )
    lines.extend(["", "## Released seal statements", ""])
    for subject in packet["subjects"]:
        if subject.get("release_state") == "released":
            lines.append(
                release_seal_markdown(
                    case_id=case_id, subject_id=subject["subject_id"]
                ).strip()
            )
            lines.append("")
    return "\n".join(lines) + "\n"
