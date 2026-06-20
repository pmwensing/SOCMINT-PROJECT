from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import database as db
from .artifacts import artifact_root

SCHEMA = "socmint.candidate_profile_review.v12_10_4"
VALID_ACTIONS = {
    "accept_same_entity",
    "reject_collision",
    "mark_uncertain",
    "request_more_evidence",
}
ACTION_TO_STATE = {
    "accept_same_entity": "accepted",
    "reject_collision": "rejected",
    "mark_uncertain": "uncertain",
    "request_more_evidence": "needs_more_evidence",
}


def _decision_dir() -> Path:
    path = artifact_root() / "candidate-profile-review-decisions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _decision_path(subject_id: int) -> Path:
    return _decision_dir() / f"subject-{int(subject_id)}.json"


def _load_decisions(subject_id: int) -> dict[str, Any]:
    path = _decision_path(subject_id)
    if not path.exists():
        return {"schema": SCHEMA, "subject_id": subject_id, "decisions": {}}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {"schema": SCHEMA, "subject_id": subject_id, "decisions": {}}
    data.setdefault("schema", SCHEMA)
    data.setdefault("subject_id", subject_id)
    data.setdefault("decisions", {})
    return data


def _save_decisions(subject_id: int, data: dict[str, Any]) -> None:
    data["schema"] = SCHEMA
    data["subject_id"] = subject_id
    data["updated_at"] = datetime.now(UTC).isoformat()
    _decision_path(subject_id).write_text(json.dumps(data, indent=2, sort_keys=True))


def list_profile_review_decisions(subject_id: int) -> dict[str, Any]:
    return _load_decisions(subject_id)


def _find_candidate(
    profile_payload: dict[str, Any], candidate_id: str
) -> dict[str, Any] | None:
    for candidate in profile_payload.get("candidates") or []:
        if str(candidate.get("candidate_id")) == str(candidate_id):
            return candidate
    return None


def _assertion_value(candidate: dict[str, Any]) -> str:
    fp = candidate.get("profile_fingerprint") or {}
    return (
        fp.get("profile_url")
        or f"{fp.get('platform', 'unknown')}:{fp.get('username', candidate.get('candidate_id'))}"
    )


def _create_or_confirm_assertion(
    subject_id: int, candidate: dict[str, Any], actor: str | None, note: str | None
) -> int:
    value = _assertion_value(candidate)
    payload = {
        "schema": SCHEMA,
        "candidate_id": candidate.get("candidate_id"),
        "relationship": candidate.get("identity_link_hypothesis", {}).get(
            "relationship"
        ),
        "identity_score": candidate.get("identity_score"),
        "collision_status": candidate.get("collision_status"),
        "profile_fingerprint": candidate.get("profile_fingerprint"),
        "source_refs": candidate.get("source_refs", []),
        "evidence_refs": candidate.get("evidence_refs", []),
        "review": {"actor": actor, "note": note, "action": "accept_same_entity"},
    }
    return db.upsert_spine_assertion(
        subject_id=subject_id,
        assertion_type="same_online_identity_cluster",
        normalized_value=value,
        confidence=str(candidate.get("identity_score") or 0.0),
        validation_state="confirmed",
        payload=payload,
    )


def review_candidate_profile(
    subject_id: int,
    candidate_id: str,
    action: str,
    profile_payload: dict[str, Any],
    actor: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    action = str(action or "").strip()
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unsupported candidate review action: {action}")
    candidate = _find_candidate(profile_payload, candidate_id)
    if not candidate:
        raise ValueError(f"Candidate profile not found: {candidate_id}")
    state = ACTION_TO_STATE[action]
    decision = {
        "schema": SCHEMA,
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "action": action,
        "review_state": state,
        "actor": actor,
        "note": note,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "identity_score": candidate.get("identity_score"),
        "collision_status": candidate.get("collision_status"),
        "profile_fingerprint": candidate.get("profile_fingerprint"),
        "positive_reasons": candidate.get("positive_reasons", []),
        "negative_reasons": candidate.get("negative_reasons", []),
    }
    assertion_id = None
    if action == "accept_same_entity":
        assertion_id = _create_or_confirm_assertion(subject_id, candidate, actor, note)
        decision["assertion_id"] = assertion_id
    data = _load_decisions(subject_id)
    data["decisions"][candidate_id] = decision
    _save_decisions(subject_id, data)
    return {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "candidate_id": candidate_id,
        "action": action,
        "review_state": state,
        "assertion_id": assertion_id,
    }


def apply_profile_review_decisions(
    profile_payload: dict[str, Any], subject_id: int
) -> dict[str, Any]:
    decisions = _load_decisions(subject_id).get("decisions", {})
    accepted = rejected = uncertain = needs_more_evidence = unreviewed = (
        dossier_ready
    ) = 0
    for candidate in profile_payload.get("candidates") or []:
        candidate_id = str(candidate.get("candidate_id"))
        decision = decisions.get(candidate_id)
        if decision:
            state = decision.get("review_state", "unreviewed")
            candidate["analyst_review"]["review_state"] = state
            candidate["analyst_review"]["decision"] = decision
            candidate["analyst_review"]["reviewed_at"] = decision.get("reviewed_at")
            candidate["analyst_review"]["actor"] = decision.get("actor")
            if state == "accepted":
                accepted += 1
                candidate["identity_link_hypothesis"][
                    "can_promote_to_dossier_assertion"
                ] = True
                candidate["dossier_assertion_gate"]["dossier_ready"] = True
                candidate["dossier_assertion_gate"]["blocked_reason"] = None
                candidate["dossier_assertion_gate"]["assertion_id"] = decision.get(
                    "assertion_id"
                )
                candidate["dossier_assertion_gate"]["assertion_type"] = (
                    "same_online_identity_cluster"
                )
                dossier_ready += 1
            elif state == "rejected":
                rejected += 1
                candidate["dossier_assertion_gate"]["dossier_ready"] = False
                candidate["dossier_assertion_gate"]["blocked_reason"] = (
                    "Analyst rejected this candidate as a collision."
                )
            elif state == "uncertain":
                uncertain += 1
                candidate["dossier_assertion_gate"]["blocked_reason"] = (
                    "Analyst marked this candidate uncertain."
                )
            elif state == "needs_more_evidence":
                needs_more_evidence += 1
                candidate["dossier_assertion_gate"]["blocked_reason"] = (
                    "Analyst requested more evidence before identity linkage."
                )
            else:
                unreviewed += 1
        else:
            unreviewed += 1
        candidate["dossier_ready"] = bool(
            candidate.get("dossier_assertion_gate", {}).get("dossier_ready")
        )
    profile_payload["review_decision_counts"] = {
        "accepted": accepted,
        "rejected": rejected,
        "uncertain": uncertain,
        "needs_more_evidence": needs_more_evidence,
        "unreviewed": unreviewed,
    }
    profile_payload["needs_review_count"] = unreviewed + uncertain + needs_more_evidence
    profile_payload["dossier_ready_count"] = dossier_ready
    profile_payload["gate"] = {
        "status": "review" if profile_payload.get("candidate_count") else "empty",
        "rule": "Accepted candidates can become confirmed same-online-identity assertions. Rejected candidates are excluded. Uncertain and more-evidence candidates remain in review.",
    }
    return profile_payload


def export_profile_review_report(
    subject_id: int, profile_payload: dict[str, Any], fmt: str = "json"
) -> tuple[str, str, str]:
    fmt = (fmt or "json").lower().strip()
    payload = apply_profile_review_decisions(profile_payload, subject_id)
    if fmt == "md" or fmt == "markdown":
        lines = [
            f"# Candidate Profile Review Report — Subject {subject_id}",
            "",
            f"Schema: `{SCHEMA}`",
            "",
            "## Summary",
            "",
            f"- Candidate profiles: {payload.get('candidate_count', 0)}",
            f"- Dossier-ready accepted candidates: {payload.get('dossier_ready_count', 0)}",
            f"- Review queue: {payload.get('needs_review_count', 0)}",
            "",
            "## Candidates",
            "",
        ]
        for candidate in payload.get("candidates") or []:
            fp = candidate.get("profile_fingerprint") or {}
            lines.extend(
                [
                    f"### {candidate.get('candidate_id')} — {fp.get('platform') or 'unknown'} / {fp.get('username') or 'unknown'}",
                    "",
                    f"- Profile URL: {fp.get('profile_url') or 'n/a'}",
                    f"- Identity score: {candidate.get('identity_score')}",
                    f"- Collision status: {candidate.get('collision_status')}",
                    f"- Review state: {candidate.get('analyst_review', {}).get('review_state')}",
                    f"- Dossier ready: {candidate.get('dossier_ready')}",
                    f"- Positive reasons: {'; '.join(candidate.get('positive_reasons') or []) or 'n/a'}",
                    f"- Negative reasons: {'; '.join(candidate.get('negative_reasons') or []) or 'n/a'}",
                    "",
                ]
            )
        return (
            "text/markdown",
            f"candidate-profile-review-subject-{subject_id}.md",
            "\n".join(lines),
        )
    return (
        "application/json",
        f"candidate-profile-review-subject-{subject_id}.json",
        json.dumps(payload, indent=2, sort_keys=True),
    )
