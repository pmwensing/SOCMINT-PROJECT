from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import database as db
from .artifacts import artifact_root

SCHEMA = "socmint.entity_alias_review.v12_10_7"
VALID_ALIAS_ACTIONS = {
    "confirm_alias",
    "reject_alias",
    "mark_alias_uncertain",
    "request_alias_evidence",
}
ALIAS_ACTION_TO_STATE = {
    "confirm_alias": "confirmed",
    "reject_alias": "rejected",
    "mark_alias_uncertain": "uncertain",
    "request_alias_evidence": "needs_more_evidence",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _review_dir() -> Path:
    path = artifact_root() / "entity-alias-review-decisions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _review_path(subject_id: int) -> Path:
    return _review_dir() / f"subject-{int(subject_id)}.json"


def _empty(subject_id: int) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "alias_decisions": {},
        "clusters": {},
        "events": [],
    }


def _load(subject_id: int) -> dict[str, Any]:
    path = _review_path(subject_id)
    if not path.exists():
        return _empty(subject_id)
    try:
        data = json.loads(path.read_text())
    except Exception:
        return _empty(subject_id)
    data.setdefault("schema", SCHEMA)
    data.setdefault("subject_id", subject_id)
    data.setdefault("alias_decisions", {})
    data.setdefault("clusters", {})
    data.setdefault("events", [])
    return data


def _save(subject_id: int, data: dict[str, Any]) -> None:
    data["schema"] = SCHEMA
    data["subject_id"] = subject_id
    data["updated_at"] = utc_now()
    _review_path(subject_id).write_text(json.dumps(data, indent=2, sort_keys=True))


def list_alias_review_decisions(subject_id: int) -> dict[str, Any]:
    return _load(subject_id)


def find_alias(alias_graph: dict[str, Any], alias_id: str) -> dict[str, Any] | None:
    for alias in alias_graph.get("aliases") or []:
        if str(alias.get("alias_id")) == str(alias_id):
            return alias
    return None


def cluster_id_for_aliases(alias_ids: list[str]) -> str:
    seed = "|".join(sorted(str(item) for item in alias_ids if item))
    return "cluster-" + hashlib.sha256(seed.encode()).hexdigest()[:20]


def review_entity_alias(
    subject_id: int,
    alias_id: str,
    action: str,
    alias_graph: dict[str, Any],
    actor: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    action = str(action or "").strip()
    if action not in VALID_ALIAS_ACTIONS:
        raise ValueError(f"Unsupported alias review action: {action}")
    alias = find_alias(alias_graph, alias_id)
    if not alias:
        raise ValueError(f"Entity alias not found: {alias_id}")
    state = ALIAS_ACTION_TO_STATE[action]
    timestamp = utc_now()
    data = _load(subject_id)
    decision = {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "alias_id": alias_id,
        "action": action,
        "review_state": state,
        "actor": actor,
        "note": note,
        "reviewed_at": timestamp,
        "alias_type": alias.get("alias_type"),
        "normalized_value": alias.get("normalized_value"),
        "confidence": alias.get("confidence"),
        "evidence_refs": alias.get("evidence_refs", []),
        "candidate_ids": alias.get("candidate_ids", []),
    }
    data["alias_decisions"][alias_id] = decision
    data["events"].append(
        {
            "event": "alias_reviewed",
            "timestamp": timestamp,
            "alias_id": alias_id,
            "action": action,
            "state": state,
            "actor": actor,
            "note": note,
        }
    )
    _save(subject_id, data)
    return {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "alias_id": alias_id,
        "action": action,
        "review_state": state,
    }


def merge_alias_cluster(
    subject_id: int,
    alias_ids: list[str],
    alias_graph: dict[str, Any],
    actor: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    ids = sorted({str(item).strip() for item in alias_ids if str(item).strip()})
    if len(ids) < 2:
        raise ValueError(
            "At least two alias IDs are required to create an identity cluster."
        )
    missing = [alias_id for alias_id in ids if not find_alias(alias_graph, alias_id)]
    if missing:
        raise ValueError(f"Alias IDs not found: {', '.join(missing)}")
    timestamp = utc_now()
    cluster_id = cluster_id_for_aliases(ids)
    data = _load(subject_id)
    cluster = data["clusters"].setdefault(
        cluster_id,
        {"cluster_id": cluster_id, "alias_ids": [], "state": "merged", "events": []},
    )
    cluster["alias_ids"] = sorted(set(cluster.get("alias_ids", []) + ids))
    cluster["state"] = "merged"
    cluster["note"] = note
    cluster["updated_at"] = timestamp
    cluster["events"].append(
        {
            "event": "aliases_clustered",
            "timestamp": timestamp,
            "alias_ids": ids,
            "actor": actor,
            "note": note,
        }
    )
    data["events"].append(
        {
            "event": "aliases_clustered",
            "timestamp": timestamp,
            "cluster_id": cluster_id,
            "alias_ids": ids,
            "actor": actor,
            "note": note,
        }
    )
    _save(subject_id, data)
    return {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "cluster_id": cluster_id,
        "alias_ids": cluster["alias_ids"],
        "state": "merged",
    }


def split_alias_from_clusters(
    subject_id: int, alias_id: str, actor: str | None = None, note: str | None = None
) -> dict[str, Any]:
    data = _load(subject_id)
    changed: list[str] = []
    timestamp = utc_now()
    for cluster_id, cluster in data.get("clusters", {}).items():
        if alias_id in cluster.get("alias_ids", []):
            cluster["alias_ids"] = [
                item for item in cluster.get("alias_ids", []) if item != alias_id
            ]
            cluster["updated_at"] = timestamp
            cluster.setdefault("events", []).append(
                {
                    "event": "alias_split",
                    "timestamp": timestamp,
                    "alias_id": alias_id,
                    "actor": actor,
                    "note": note,
                }
            )
            changed.append(cluster_id)
    data["events"].append(
        {
            "event": "alias_split",
            "timestamp": timestamp,
            "alias_id": alias_id,
            "clusters": changed,
            "actor": actor,
            "note": note,
        }
    )
    _save(subject_id, data)
    return {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "alias_id": alias_id,
        "split_from_clusters": changed,
    }


def apply_alias_review_decisions(
    alias_graph: dict[str, Any], subject_id: int
) -> dict[str, Any]:
    data = _load(subject_id)
    decisions = data.get("alias_decisions", {})
    clusters = data.get("clusters", {})
    alias_to_clusters: dict[str, list[str]] = {}
    for cluster_id, cluster in clusters.items():
        if cluster.get("state") != "merged":
            continue
        for alias_id in cluster.get("alias_ids", []):
            alias_to_clusters.setdefault(alias_id, []).append(cluster_id)
    counts = {
        "confirmed": 0,
        "rejected": 0,
        "uncertain": 0,
        "needs_more_evidence": 0,
        "candidate": 0,
    }
    promotable = 0
    for alias in alias_graph.get("aliases") or []:
        alias_id = str(alias.get("alias_id"))
        decision = decisions.get(alias_id)
        if decision:
            alias["analyst_state"] = decision.get(
                "review_state", alias.get("analyst_state")
            )
            alias["alias_review"] = decision
        else:
            alias.setdefault(
                "alias_review",
                {"review_state": alias.get("analyst_state", "candidate")},
            )
        alias["identity_cluster_ids"] = alias_to_clusters.get(alias_id, [])
        alias["can_promote_to_dossier_assertion"] = (
            alias.get("analyst_state") == "confirmed"
        )
        if alias["can_promote_to_dossier_assertion"]:
            promotable += 1
        state = alias.get("analyst_state", "candidate")
        counts[state] = counts.get(state, 0) + 1
    alias_graph["alias_review"] = {
        "schema": SCHEMA,
        "decision_counts": counts,
        "cluster_count": len(
            [c for c in clusters.values() if c.get("state") == "merged"]
        ),
        "clusters": clusters,
        "promotable_alias_count": promotable,
        "rule": "Only analyst-confirmed aliases can be promoted into dossier assertions. Clusters group aliases; split removes an alias from a cluster.",
    }
    alias_graph["state_counts"] = counts
    return alias_graph


def promote_alias_to_assertion(
    subject_id: int,
    alias_id: str,
    alias_graph: dict[str, Any],
    actor: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    alias = find_alias(alias_graph, alias_id)
    if not alias:
        raise ValueError(f"Entity alias not found: {alias_id}")
    if alias.get("analyst_state") != "confirmed":
        raise ValueError(
            "Only analyst-confirmed aliases can be promoted to dossier assertions."
        )
    payload = {
        "schema": SCHEMA,
        "alias_id": alias_id,
        "alias_type": alias.get("alias_type"),
        "alias_value": alias.get("alias_value"),
        "normalized_value": alias.get("normalized_value"),
        "confidence": alias.get("confidence"),
        "evidence_refs": alias.get("evidence_refs", []),
        "candidate_ids": alias.get("candidate_ids", []),
        "identity_cluster_ids": alias.get("identity_cluster_ids", []),
        "review": {
            "actor": actor,
            "note": note,
            "action": "promote_alias_to_assertion",
        },
    }
    assertion_id = db.upsert_spine_assertion(
        subject_id=subject_id,
        assertion_type="entity_alias_confirmed",
        normalized_value=f"{alias.get('alias_type')}:{alias.get('normalized_value')}",
        confidence=str(alias.get("confidence") or 0.0),
        validation_state="confirmed",
        payload=payload,
    )
    return {
        "schema": SCHEMA,
        "subject_id": subject_id,
        "alias_id": alias_id,
        "assertion_id": assertion_id,
        "assertion_type": "entity_alias_confirmed",
    }
