from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from . import database
from .dossier_assembly_workspace_v21_0 import _ensure_storage, _json_details, _sha
from .portfolio_operations_dashboard_v24_0 import build_portfolio_operations_dashboard

SCHEMA = "socmint.global_investigation_search.v27_0"
VERSION = "v27.0.0"
RESULT_TYPES = (
    "case",
    "entity",
    "identifier",
    "infrastructure",
    "evidence",
    "finding",
    "timeline",
    "review",
    "collaboration",
    "closure",
    "archive",
    "cross_case",
)


def _tokens(value: str) -> list[str]:
    return [item for item in re.findall(r"[a-z0-9@._:+-]+", value.lower()) if item]


def _record_type(action: str, details: dict[str, Any]) -> str:
    text = " ".join((action, *map(str, details.keys()))).lower()
    if "archive" in text:
        return "archive"
    if "closure" in text or "retention" in text or "reopen" in text:
        return "closure"
    if (
        "collaboration" in text
        or "team_role" in text
        or "handoff" in text
        or "mention" in text
    ):
        return "collaboration"
    if "cross_case" in text or "confirmed_link" in text or "correlation" in text:
        return "cross_case"
    if "finding" in text:
        return "finding"
    if "evidence" in text or "citation" in text or "source" in text:
        return "evidence"
    if "entity" in text or any(key in details for key in ("entity_id", "entity_type")):
        return "entity"
    if "identifier" in text or any(
        key in details for key in ("email", "phone", "username", "domain", "ip_address")
    ):
        return "identifier"
    if "infrastructure" in text or any(
        key in details for key in ("host", "url", "domain", "ip")
    ):
        return "infrastructure"
    if "timeline" in text or "event" in text:
        return "timeline"
    if "review" in text or "decision" in text or "approval" in text:
        return "review"
    return "case"


def _display(action: str, case_id: str, details: dict[str, Any]) -> tuple[str, str]:
    for key in (
        "title",
        "name",
        "label",
        "display_value",
        "match_value",
        "finding",
        "summary",
        "subject",
    ):
        value = details.get(key)
        if value not in (None, ""):
            title = str(value)
            break
    else:
        title = action.replace("_", " ").title()
    summary_fields = []
    for key in (
        "status",
        "decision",
        "reason",
        "note",
        "description",
        "category",
        "role",
        "stage",
    ):
        value = details.get(key)
        if value not in (None, ""):
            summary_fields.append(f"{key.replace('_', ' ')}: {value}")
    summary = " · ".join(summary_fields[:4]) or f"Case {case_id} · {action}"
    return title[:240], summary[:600]


def _links(case_id: str, result_type: str) -> dict[str, str]:
    links = {
        "case": f"/case-intelligence-review/{case_id}",
        "evidence": f"/dossier-assembly/{case_id}",
        "review": f"/case-intelligence-review/{case_id}",
        "collaboration": f"/cases/{case_id}/collaboration-notes",
        "closure": f"/case-closure/{case_id}",
        "archive": f"/case-closure/{case_id}/history",
        "cross_case": "/cross-case-intelligence",
    }
    links["primary"] = links.get(result_type, links["case"])
    return links


def _searchable_text(record: dict[str, Any]) -> str:
    return " ".join(
        (
            str(record.get("case_id") or ""),
            str(record.get("action") or ""),
            str(record.get("actor") or ""),
            json.dumps(record.get("details") or {}, sort_keys=True, default=str),
        )
    ).lower()


def _score(query: str, record: dict[str, Any]) -> tuple[float, list[str]]:
    query_l = query.lower().strip()
    text = _searchable_text(record)
    query_tokens = _tokens(query_l)
    matched = sorted({token for token in query_tokens if token in text})
    if not query_tokens:
        return 0.0, []
    score = 0.0
    if query_l == str(record.get("case_id") or "").lower():
        score += 100.0
    if query_l in text:
        score += 40.0
    score += 12.0 * len(matched)
    score += 20.0 * (len(matched) / len(query_tokens))
    return round(score, 3), matched


def _audit_records() -> list[dict[str, Any]]:
    _ensure_storage()
    session = database.Session()
    try:
        rows = (
            session.query(database.AuditLog)
            .order_by(database.AuditLog.created_at.desc(), database.AuditLog.id.desc())
            .all()
        )
        return [
            {
                "record_id": row.id,
                "case_id": str(row.target_value or "").strip(),
                "action": str(row.action or ""),
                "actor": row.actor,
                "occurred_at": row.created_at.isoformat() if row.created_at else None,
                "details": _json_details(row),
            }
            for row in rows
            if str(row.target_value or "").strip()
        ]
    finally:
        session.close()


def _case_records() -> list[dict[str, Any]]:
    cases = build_portfolio_operations_dashboard().get("cases") or []
    return [
        {
            "record_id": f"case:{item.get('case_id')}",
            "case_id": str(item.get("case_id") or ""),
            "action": "portfolio_case",
            "actor": item.get("latest_actor"),
            "occurred_at": item.get("latest_activity_at"),
            "details": item,
        }
        for item in cases
        if item.get("case_id")
    ]


def build_global_investigation_search(
    query: str = "",
    *,
    result_types: list[str] | tuple[str, ...] | set[str] | None = None,
    allowed_case_ids: set[str] | None = None,
    limit: int = 100,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    query = str(query or "").strip()
    requested_types = {
        str(item) for item in (result_types or []) if str(item) in RESULT_TYPES
    }
    visible = (
        None if allowed_case_ids is None else {str(item) for item in allowed_case_ids}
    )
    source = (
        list(records) if records is not None else _case_records() + _audit_records()
    )
    normalized = []
    for record in source:
        case_id = str(record.get("case_id") or "").strip()
        if not case_id or (visible is not None and case_id not in visible):
            continue
        details = dict(record.get("details") or {})
        result_type = _record_type(str(record.get("action") or ""), details)
        if requested_types and result_type not in requested_types:
            continue
        score, matched_terms = _score(query, record)
        if query and not matched_terms and score <= 0:
            continue
        title, summary = _display(str(record.get("action") or ""), case_id, details)
        binding = {
            "source_record_id": record.get("record_id"),
            "source_action": record.get("action"),
            "case_id": case_id,
        }
        normalized.append(
            {
                "result_id": f"search-result-{record.get('record_id')}",
                "result_type": result_type,
                "case_id": case_id,
                "title": title,
                "summary": summary,
                "score": score,
                "matched_terms": matched_terms,
                "actor": record.get("actor"),
                "occurred_at": record.get("occurred_at"),
                "source_action": record.get("action"),
                "source_record_id": record.get("record_id"),
                "source_binding": binding,
                "source_binding_sha256": _sha(binding),
                "links": _links(case_id, result_type),
                "access_scope": {"case_id": case_id, "visible": True},
            }
        )
    normalized.sort(
        key=lambda item: (
            item["score"],
            item.get("occurred_at") or "",
            item["result_id"],
        ),
        reverse=True,
    )
    normalized = normalized[: max(1, min(int(limit or 100), 500))]
    counts = Counter(item["result_type"] for item in normalized)
    query_contract = {
        "query": query,
        "tokens": _tokens(query),
        "result_types": sorted(requested_types),
        "limit": max(1, min(int(limit or 100), 500)),
    }
    core = {"query_contract": query_contract, "results": normalized}
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "query": query,
        "query_contract": query_contract,
        "result_types": list(RESULT_TYPES),
        "results": normalized,
        "result_count": len(normalized),
        "result_type_counts": dict(sorted(counts.items())),
        "visible_case_ids": sorted({item["case_id"] for item in normalized}),
        "access_scope": {
            "mode": "restricted"
            if allowed_case_ids is not None
            else "all_visible_cases",
            "allowed_case_ids": sorted(visible) if visible is not None else None,
        },
        "search_sha256": _sha(core),
        "read_only": True,
        "source_records_mutated": False,
        "search_record_created": False,
        "case_access_scope_changed": False,
        "next_action": "refine_global_investigation_search"
        if query
        else "enter_global_search_query",
    }
