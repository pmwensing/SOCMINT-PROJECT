from __future__ import annotations

import ipaddress
import json
import re
from collections import Counter, defaultdict
from typing import Any, Iterable
from urllib.parse import urlparse

from . import database
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details, _sha

SCHEMA = "socmint.cross_case_intelligence_workspace.v25_0"
VERSION = "v25.0.0"

ENTITY_KEYS = {
    "entity",
    "entity_id",
    "subject",
    "subject_id",
    "person",
    "person_id",
    "profile",
    "profile_id",
    "display_name",
    "full_name",
    "name",
}
IDENTIFIER_KEYS = {
    "identifier",
    "identifier_value",
    "username",
    "user_name",
    "handle",
    "email",
    "email_address",
    "phone",
    "phone_number",
    "account_id",
    "external_id",
    "uid",
}
INFRASTRUCTURE_KEYS = {
    "domain",
    "hostname",
    "host",
    "ip",
    "ip_address",
    "ipv4",
    "ipv6",
    "url",
    "uri",
    "website",
    "endpoint",
}
EVIDENCE_KEYS = {
    "evidence",
    "evidence_id",
    "artifact",
    "artifact_id",
    "claim",
    "claim_id",
    "assertion",
    "assertion_id",
    "source",
    "source_id",
    "capture",
    "capture_id",
    "document_id",
    "media_id",
}
TIMELINE_KEYS = {
    "event",
    "event_id",
    "event_type",
    "occurred_at",
    "observed_at",
    "captured_at",
    "published_at",
    "timestamp",
    "date",
    "datetime",
    "time",
}
IGNORED_VALUES = {
    "",
    "none",
    "null",
    "true",
    "false",
    "unknown",
    "ready",
    "complete",
    "completed",
    "active",
    "blocked",
    "failed",
    "success",
    "saved",
    "recorded",
}


def _normalize_scalar(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return str(value)
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().split())
    if not normalized or normalized.lower() in IGNORED_VALUES:
        return None
    return normalized


def _normalized_match_value(category: str, value: str) -> str:
    candidate = value.strip()
    if category in {"identifier", "infrastructure"}:
        candidate = candidate.lower()
    if category == "infrastructure":
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
        parsed = urlparse(candidate if "://" in candidate else f"//{candidate}")
        if parsed.hostname:
            return parsed.hostname.lower().rstrip(".")
    if category == "identifier" and "@" in candidate:
        return candidate.lower()
    return candidate.casefold()


def _category_for(key: str, value: str) -> str | None:
    key_name = key.lower().strip()
    if key_name in ENTITY_KEYS or key_name.endswith("_entity_id"):
        return "entity"
    if key_name in IDENTIFIER_KEYS or key_name.endswith(
        ("_username", "_handle", "_email")
    ):
        return "identifier"
    if key_name in INFRASTRUCTURE_KEYS or key_name.endswith(
        ("_domain", "_hostname", "_ip", "_url")
    ):
        return "infrastructure"
    if key_name in EVIDENCE_KEYS or key_name.endswith(
        ("_evidence_id", "_artifact_id", "_claim_id", "_assertion_id")
    ):
        return "evidence"
    if key_name in TIMELINE_KEYS or key_name.endswith(("_at", "_date", "_timestamp")):
        return "timeline"
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return "identifier"
    try:
        ipaddress.ip_address(value)
        return "infrastructure"
    except ValueError:
        return None


def _walk(value: Any, path: str = "") -> Iterable[tuple[str, str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if isinstance(child, (dict, list, tuple)):
                yield from _walk(child, child_path)
                continue
            scalar = _normalize_scalar(child)
            if scalar is not None:
                category = _category_for(str(key), scalar)
                if category:
                    yield category, scalar, child_path
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _case_audit_records() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .filter(database.AuditLog.target_value.isnot(None))
            .order_by(database.AuditLog.created_at.asc(), database.AuditLog.id.asc())
            .all()
        )
        records = []
        for row in rows:
            case_id = str(row.target_value or "").strip()
            if not case_id:
                continue
            action = str(row.action or "")
            details = _json_details(row)
            if not isinstance(details, dict):
                continue
            records.append(
                {
                    "case_id": case_id,
                    "record_id": row.id,
                    "action": action,
                    "actor": row.actor,
                    "occurred_at": row.created_at.isoformat()
                    if row.created_at
                    else None,
                    "details": details,
                }
            )
        return records
    finally:
        session.close()


def _visible_records(
    records: list[dict[str, Any]], allowed_case_ids: set[str] | None
) -> list[dict[str, Any]]:
    if allowed_case_ids is None:
        return records
    return [record for record in records if record["case_id"] in allowed_case_ids]


def build_cross_case_intelligence_workspace(
    *,
    allowed_case_ids: set[str] | None = None,
    minimum_case_count: int = 2,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    minimum = max(2, int(minimum_case_count))
    source_records = _visible_records(
        records if records is not None else _case_audit_records(), allowed_case_ids
    )

    values: dict[tuple[str, str], dict[str, Any]] = {}
    case_actions: dict[str, Counter[str]] = defaultdict(Counter)
    blocker_cases: dict[str, set[str]] = defaultdict(set)
    case_provenance: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in source_records:
        case_id = record["case_id"]
        action = record["action"]
        case_actions[case_id][action] += 1
        details = record.get("details") or {}
        for blocker in details.get("blockers") or []:
            if isinstance(blocker, dict):
                key = str(blocker.get("key") or "").strip()
                if key:
                    blocker_cases[key].add(case_id)

        provenance_base = {
            "case_id": case_id,
            "record_id": record.get("record_id"),
            "source_action": action,
            "actor": record.get("actor"),
            "occurred_at": record.get("occurred_at"),
        }
        case_provenance[case_id].append(provenance_base)

        for category, display_value, path in _walk(details):
            match_value = _normalized_match_value(category, display_value)
            key = (category, match_value)
            entry = values.setdefault(
                key,
                {
                    "category": category,
                    "match_value": match_value,
                    "display_values": set(),
                    "case_ids": set(),
                    "occurrences": [],
                },
            )
            occurrence = {
                **provenance_base,
                "field_path": path,
                "display_value": display_value,
            }
            occurrence["provenance_sha256"] = _sha(occurrence)
            entry["display_values"].add(display_value)
            entry["case_ids"].add(case_id)
            entry["occurrences"].append(occurrence)

    correlations: dict[str, list[dict[str, Any]]] = {
        "entities": [],
        "identifiers": [],
        "infrastructure": [],
        "evidence": [],
        "timelines": [],
    }
    plural = {
        "entity": "entities",
        "identifier": "identifiers",
        "infrastructure": "infrastructure",
        "evidence": "evidence",
        "timeline": "timelines",
    }
    for entry in values.values():
        if len(entry["case_ids"]) < minimum:
            continue
        item = {
            "correlation_id": f"cross-case-{entry['category']}-{_sha({'category': entry['category'], 'match_value': entry['match_value']})[:20]}",
            "category": entry["category"],
            "match_value": entry["match_value"],
            "display_values": sorted(entry["display_values"]),
            "case_ids": sorted(entry["case_ids"]),
            "case_count": len(entry["case_ids"]),
            "occurrence_count": len(entry["occurrences"]),
            "occurrences": sorted(
                entry["occurrences"],
                key=lambda value: (
                    value.get("occurred_at") or "",
                    int(value.get("record_id") or 0),
                    value.get("field_path") or "",
                ),
            ),
            "human_review_required": True,
            "confirmed_match": False,
        }
        correlations[plural[entry["category"]]].append(item)

    for items in correlations.values():
        items.sort(
            key=lambda item: (
                -item["case_count"],
                -item["occurrence_count"],
                item["match_value"],
            )
        )

    action_patterns = []
    all_actions = sorted(
        {action for counts in case_actions.values() for action in counts}
    )
    for action in all_actions:
        participating = {
            case_id: counts[action]
            for case_id, counts in case_actions.items()
            if counts[action] > 0
        }
        if len(participating) >= minimum:
            action_patterns.append(
                {
                    "pattern_type": "repeated_action",
                    "pattern": action,
                    "case_ids": sorted(participating),
                    "case_count": len(participating),
                    "occurrence_count": sum(participating.values()),
                    "counts_by_case": dict(sorted(participating.items())),
                    "human_review_required": True,
                }
            )

    blocker_patterns = [
        {
            "pattern_type": "repeated_blocker",
            "pattern": blocker,
            "case_ids": sorted(case_ids),
            "case_count": len(case_ids),
            "human_review_required": True,
        }
        for blocker, case_ids in blocker_cases.items()
        if len(case_ids) >= minimum
    ]
    patterns = sorted(
        action_patterns + blocker_patterns,
        key=lambda item: (-item["case_count"], item["pattern_type"], item["pattern"]),
    )

    case_ids = sorted({record["case_id"] for record in source_records})
    counts = {
        "visible_cases": len(case_ids),
        "source_records": len(source_records),
        "entity_correlations": len(correlations["entities"]),
        "identifier_correlations": len(correlations["identifiers"]),
        "infrastructure_correlations": len(correlations["infrastructure"]),
        "evidence_correlations": len(correlations["evidence"]),
        "timeline_correlations": len(correlations["timelines"]),
        "repeated_patterns": len(patterns),
    }

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "minimum_case_count": minimum,
        "access_scope": {
            "mode": "restricted"
            if allowed_case_ids is not None
            else "all_visible_cases",
            "allowed_case_ids": sorted(allowed_case_ids)
            if allowed_case_ids is not None
            else None,
            "visible_case_ids": case_ids,
        },
        "counts": counts,
        "correlations": correlations,
        "repeated_patterns": patterns,
        "case_provenance": {
            case_id: sorted(
                records,
                key=lambda value: (
                    value.get("occurred_at") or "",
                    int(value.get("record_id") or 0),
                ),
            )
            for case_id, records in sorted(case_provenance.items())
        },
        "links": {
            "portfolio_operations": "/portfolio-operations",
            "portfolio_history": "/portfolio-operations/history",
        },
        "human_review_required": True,
        "correlations_are_candidates": True,
        "source_records_mutated": False,
        "correlation_record_created": False,
        "next_action": "review_cross_case_candidates",
    }
