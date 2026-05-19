from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from .assertion_trust_gate_v12_8_1 import assertion_release_gate, assertion_trust_summary
from .authenticity_integrity_v12_7 import integrity_dashboard_payload
from .forensic_intake_v12_5 import intake_dashboard_payload
from .integrity_gate_v12_7_1 import integrity_release_gate
from .narrative_export_v12_6_1 import narrative_dashboard_polish_payload
from .production_gate_v12 import production_release_gate

SCHEMA = "socmint.guided_investigation.v12_9"


@dataclass
class ProgressStep:
    key: str
    label: str
    status: str
    score: float
    href: str
    detail: str
    actions: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _status_from_counts(good: int, review: int = 0, bad: int = 0, empty: bool = False) -> str:
    if bad > 0:
        return "red"
    if empty or review > 0:
        return "yellow"
    if good > 0:
        return "green"
    return "yellow"


def _score_for_status(status: str) -> float:
    return {"green": 1.0, "yellow": 0.55, "red": 0.15}.get(status, 0.0)


def _action(priority: str, label: str, href: str, reason: str) -> dict[str, Any]:
    return {"priority": priority, "label": label, "href": href, "reason": reason}


def evidence_step(root: str | None = None) -> ProgressStep:
    intake = intake_dashboard_payload(root=root)
    latest = intake.get("latest_manifest") or {}
    item_count = int(latest.get("item_count") or 0)
    pending_count = int(intake.get("pending_count") or 0)
    status = _status_from_counts(item_count, review=pending_count, empty=item_count == 0)
    actions = []
    if pending_count:
        actions.append(_action("high", "Run forensic intake", "/forensic/intake", f"{pending_count} pending files are waiting in drop folders."))
    if item_count == 0:
        actions.append(_action("high", "Add evidence to drop folders", "/forensic/intake", "No preserved evidence is available yet."))
    return ProgressStep("evidence", "Evidence Intake", status, _score_for_status(status), "/forensic/intake", f"{item_count} preserved items · {pending_count} pending files", actions)


def integrity_step(root: str | None = None) -> ProgressStep:
    gate = integrity_release_gate(root=root)
    summary = gate.get("summary", {})
    status = {"GO": "green", "HOLD": "yellow", "FAIL": "red"}.get(gate.get("release_gate_decision"), "yellow")
    actions = []
    if summary.get("hold_count", 0):
        actions.append(_action("critical", "Resolve hold evidence", "/evidence/integrity/gate", "One or more evidence items are on hold."))
    if summary.get("review_count", 0):
        actions.append(_action("high", "Review flagged evidence", "/evidence/integrity/gate", "Flagged evidence must be reviewed before dossier use."))
    if summary.get("item_count", 0) == 0:
        actions.append(_action("high", "Run evidence integrity after intake", "/evidence/integrity", "No integrity-scored evidence exists yet."))
    return ProgressStep("integrity", "Integrity Gate", status, _score_for_status(status), "/evidence/integrity/gate", f"Decision {gate.get('release_gate_decision')} · usable {summary.get('usable_count', 0)} · review {summary.get('review_count', 0)} · hold {summary.get('hold_count', 0)}", actions)


def narrative_step(subject_id: int | None = None, root: str | None = None) -> ProgressStep:
    polish = narrative_dashboard_polish_payload(subject_id=subject_id, root=root)
    confidence = polish.get("narrative_confidence_card") or {}
    rating = confidence.get("rating") or "insufficient"
    events = len(polish.get("events") or [])
    contradictions = len(polish.get("contradiction_review_actions") or [])
    status = "green" if rating in {"strong", "moderate"} and contradictions == 0 else "yellow" if events else "yellow"
    if contradictions:
        status = "yellow"
    actions = []
    if events == 0:
        actions.append(_action("high", "Generate narrative from preserved evidence", "/narrative/storyboard", "No timeline events are available yet."))
    if contradictions:
        actions.append(_action("high", "Review narrative contradictions", "/narrative/storyboard", f"{contradictions} contradiction review actions are pending."))
    return ProgressStep("narrative", "Narrative", status, _score_for_status(status), "/narrative/storyboard", f"{events} timeline events · confidence {rating} · {contradictions} contradiction actions", actions)


def assertion_step(subject_id: int | None = None, root: str | None = None) -> ProgressStep:
    gate = assertion_release_gate(subject_id=subject_id, root=root)
    summary = gate.get("summary", {})
    status = {"GO": "green", "HOLD": "yellow", "FAIL": "red"}.get(gate.get("release_gate_decision"), "yellow")
    actions = []
    if summary.get("hold_count", 0):
        actions.append(_action("critical", "Resolve hold assertions", "/assertions/trust/gate", "Hold assertions block dossier readiness."))
    if summary.get("review_queue_count", 0):
        actions.append(_action("high", "Review assertion trust queue", "/assertions/trust/gate", f"{summary.get('review_queue_count')} assertions require analyst review."))
    if summary.get("dossier_ready_count", 0) == 0:
        actions.append(_action("high", "Build dossier-ready assertion set", "/assertions/trust", "No assertions are currently dossier-ready."))
    return ProgressStep("assertions", "Assertion Trust", status, _score_for_status(status), "/assertions/trust/gate", f"Decision {gate.get('release_gate_decision')} · ready {summary.get('dossier_ready_count', 0)} · review {summary.get('review_queue_count', 0)} · hold {summary.get('hold_count', 0)}", actions)


def release_step(subject_id: int | None = None) -> ProgressStep:
    gate = production_release_gate(subject_id=subject_id)
    status = {"GO": "green", "HOLD": "yellow", "FAIL": "red"}.get(gate.get("release_gate_decision"), "yellow")
    actions = []
    for check in gate.get("checks", []):
        if check.get("status") in {"fail", "review"}:
            actions.append(_action("critical" if check.get("status") == "fail" else "high", f"Fix {check.get('name')}", "/command-center", f"Gate check status: {check.get('status')} · actual: {check.get('actual')}"))
    return ProgressStep("release", "Release Readiness", status, _score_for_status(status), "/api/v1/production/release-gate", f"Decision {gate.get('release_gate_decision')} · {gate.get('summary', {}).get('passed_checks', 0)}/{gate.get('summary', {}).get('total_checks', 0)} checks passed", actions)


def guided_investigation_payload(subject_id: int | None = None, root: str | None = None) -> dict[str, Any]:
    steps = [
        evidence_step(root=root),
        integrity_step(root=root),
        narrative_step(subject_id=subject_id, root=root),
        assertion_step(subject_id=subject_id, root=root),
        release_step(subject_id=subject_id),
    ]
    rows = [step.as_dict() for step in steps]
    action_queue = []
    for step in rows:
        for action in step.get("actions", []):
            action_queue.append({**action, "step": step["key"], "step_label": step["label"]})
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    action_queue.sort(key=lambda item: (priority_order.get(item.get("priority"), 9), item.get("step", "")))
    readiness = "red" if any(step["status"] == "red" for step in rows) else "yellow" if any(step["status"] == "yellow" for step in rows) else "green"
    avg_score = round(sum(step["score"] for step in rows) / max(1, len(rows)), 3)
    next_action = action_queue[0] if action_queue else _action("low", "Ready for release review", "/api/v1/production/release-gate", "All guided workflow steps are green.")
    flow_edges = [
        {"source": "evidence", "target": "integrity", "label": "preserved files scored"},
        {"source": "integrity", "target": "narrative", "label": "trusted evidence builds story"},
        {"source": "narrative", "target": "assertions", "label": "claims become assertions"},
        {"source": "assertions", "target": "release", "label": "trusted assertions feed dossier"},
    ]
    return {
        "schema": SCHEMA,
        "generated_at": utc_now(),
        "subject_id": subject_id,
        "readiness": readiness,
        "readiness_score": avg_score,
        "progress_rail": rows,
        "flow_map": {"nodes": rows, "edges": flow_edges},
        "action_queue": action_queue,
        "next_action": next_action,
        "drilldowns": {
            "evidence": "/forensic/intake",
            "integrity": "/evidence/integrity/gate",
            "narrative": "/narrative/storyboard",
            "claims": "/narrative/storyboard#claims",
            "contradictions": "/narrative/storyboard#contradictions",
            "assertions": "/assertions/trust/gate",
            "release": "/api/v1/production/release-gate",
        },
        "guided_assistant": {
            "question": "What should I do next?",
            "answer": next_action.get("label"),
            "reason": next_action.get("reason"),
            "href": next_action.get("href"),
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(guided_investigation_payload(), indent=2, sort_keys=True))
