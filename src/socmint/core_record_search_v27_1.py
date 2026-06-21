from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from typing import Any

from .dossier_assembly_workspace_v21_0 import _sha
from .global_investigation_search_v27_0 import _audit_records, _case_records

SCHEMA = "socmint.core_record_search.v27_1"
VERSION = "v27.1.0"
CORE_TYPES = ("case", "entity", "evidence", "finding")

FIELD_CATALOG = {
    "case": ("case_id", "title", "stage", "status", "latest_action", "latest_actor"),
    "entity": ("entity_id", "entity_type", "name", "label", "display_value", "aliases"),
    "evidence": (
        "evidence_id",
        "title",
        "description",
        "source",
        "citation",
        "hash",
        "filename",
    ),
    "finding": (
        "finding_id",
        "finding",
        "title",
        "summary",
        "category",
        "status",
        "confidence",
    ),
}


def _tokens(value: str) -> list[str]:
    return [item for item in re.findall(r"[a-z0-9@._:+-]+", value.lower()) if item]


def _type(action: str, details: dict[str, Any]) -> str | None:
    text = " ".join((action, *map(str, details.keys()))).lower()
    if action == "portfolio_case":
        return "case"
    if "finding" in text:
        return "finding"
    if "evidence" in text or "citation" in text or "source" in text:
        return "evidence"
    if "entity" in text or any(
        key in details for key in ("entity_id", "entity_type", "aliases")
    ):
        return "entity"
    return None


def _flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def _field_values(
    record_type: str, case_id: str, details: dict[str, Any]
) -> dict[str, str]:
    values = {"case_id": case_id}
    for field in FIELD_CATALOG[record_type]:
        if field == "case_id":
            continue
        value = details.get(field)
        if value not in (None, "", [], {}):
            values[field] = _flatten(value)
    if record_type == "case":
        values.setdefault("title", details.get("title") or f"Case {case_id}")
    return values


def _match(
    query: str, fields: dict[str, str]
) -> tuple[float, list[dict[str, Any]], list[str]]:
    query_l = query.lower().strip()
    tokens = _tokens(query)
    if not query_l:
        return 0.0, [], []
    matches = []
    matched_tokens: set[str] = set()
    score = 0.0
    for field, raw in fields.items():
        value = str(raw)
        value_l = value.lower()
        exact = query_l == value_l
        phrase = query_l in value_l
        field_tokens = set(_tokens(value))
        token_hits = sorted(set(tokens) & field_tokens)
        partial_hits = sorted(
            {token for token in tokens if token in value_l and token not in token_hits}
        )
        if not (exact or phrase or token_hits or partial_hits):
            continue
        weight = 1.0
        if field.endswith("_id") or field == "case_id":
            weight = 1.8
        elif field in {"name", "title", "finding", "label", "display_value"}:
            weight = 1.5
        field_score = (
            (100 if exact else 0)
            + (45 if phrase else 0)
            + 14 * len(token_hits)
            + 7 * len(partial_hits)
        )
        field_score *= weight
        score += field_score
        matched_tokens.update(token_hits)
        matched_tokens.update(partial_hits)
        matches.append(
            {
                "field": field,
                "value": value[:500],
                "exact": exact,
                "phrase": phrase,
                "token_hits": token_hits,
                "partial_hits": partial_hits,
                "field_score": round(field_score, 3),
            }
        )
    if tokens:
        score += 25 * (len(matched_tokens) / len(tokens))
    return (
        round(score, 3),
        sorted(matches, key=lambda item: item["field_score"], reverse=True),
        sorted(matched_tokens),
    )


def _preview(
    record_type: str, fields: dict[str, str], matches: list[dict[str, Any]]
) -> dict[str, Any]:
    preferred = {
        "case": ("title", "case_id", "stage", "status"),
        "entity": ("name", "display_value", "entity_id", "entity_type", "aliases"),
        "evidence": (
            "title",
            "evidence_id",
            "description",
            "source",
            "filename",
            "hash",
        ),
        "finding": (
            "finding",
            "title",
            "finding_id",
            "summary",
            "category",
            "status",
            "confidence",
        ),
    }[record_type]
    selected = []
    seen = set()
    for match in matches:
        field = match["field"]
        if field not in seen:
            selected.append(
                {"field": field, "value": fields.get(field, "")[:300], "matched": True}
            )
            seen.add(field)
    for field in preferred:
        if field in fields and field not in seen and len(selected) < 6:
            selected.append(
                {"field": field, "value": str(fields[field])[:300], "matched": False}
            )
            seen.add(field)
    return {
        "fields": selected,
        "field_count": len(fields),
        "matched_field_count": len(matches),
    }


def _links(case_id: str, record_type: str) -> dict[str, str]:
    links = {
        "case": f"/case-intelligence-review/{case_id}",
        "entity": f"/case-intelligence-review/{case_id}",
        "evidence": f"/dossier-assembly/{case_id}",
        "finding": f"/case-intelligence-review/{case_id}",
    }
    return {
        "primary": links[record_type],
        "case": links["case"],
        "evidence": links["evidence"],
    }


def build_core_record_search(
    query: str = "",
    *,
    record_types: list[str] | tuple[str, ...] | set[str] | None = None,
    case_ids: list[str] | tuple[str, ...] | set[str] | None = None,
    actors: list[str] | tuple[str, ...] | set[str] | None = None,
    statuses: list[str] | tuple[str, ...] | set[str] | None = None,
    allowed_case_ids: set[str] | None = None,
    limit: int = 100,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    query = str(query or "").strip()
    requested_types = {
        item for item in map(str, record_types or []) if item in CORE_TYPES
    }
    requested_cases = {str(item) for item in (case_ids or []) if str(item)}
    requested_actors = {str(item) for item in (actors or []) if str(item)}
    requested_statuses = {str(item) for item in (statuses or []) if str(item)}
    visible = (
        None if allowed_case_ids is None else {str(item) for item in allowed_case_ids}
    )
    source = (
        list(records) if records is not None else _case_records() + _audit_records()
    )
    results = []
    available_facets = defaultdict(Counter)

    for record in source:
        case_id = str(record.get("case_id") or "").strip()
        if not case_id or (visible is not None and case_id not in visible):
            continue
        details = dict(record.get("details") or {})
        record_type = _type(str(record.get("action") or ""), details)
        if record_type not in CORE_TYPES:
            continue
        actor = str(record.get("actor") or "unknown")
        status = str(details.get("status") or details.get("stage") or "unspecified")
        available_facets["record_type"][record_type] += 1
        available_facets["case_id"][case_id] += 1
        available_facets["actor"][actor] += 1
        available_facets["status"][status] += 1
        if requested_types and record_type not in requested_types:
            continue
        if requested_cases and case_id not in requested_cases:
            continue
        if requested_actors and actor not in requested_actors:
            continue
        if requested_statuses and status not in requested_statuses:
            continue
        fields = _field_values(record_type, case_id, details)
        score, field_matches, matched_terms = _match(query, fields)
        if query and not field_matches:
            continue
        binding = {
            "source_record_id": record.get("record_id"),
            "source_action": record.get("action"),
            "case_id": case_id,
        }
        results.append(
            {
                "result_id": f"core-search-{record.get('record_id')}",
                "record_type": record_type,
                "case_id": case_id,
                "score": score,
                "matched_terms": matched_terms,
                "field_matches": field_matches,
                "preview": _preview(record_type, fields, field_matches),
                "actor": actor,
                "status": status,
                "occurred_at": record.get("occurred_at"),
                "source_action": record.get("action"),
                "source_record_id": record.get("record_id"),
                "source_binding": binding,
                "source_binding_sha256": _sha(binding),
                "links": _links(case_id, record_type),
                "access_scope": {"case_id": case_id, "visible": True},
                "relevance_not_confidence": True,
            }
        )

    results.sort(
        key=lambda item: (
            item["score"],
            item.get("occurred_at") or "",
            item["result_id"],
        ),
        reverse=True,
    )
    safe_limit = max(1, min(int(limit or 100), 500))
    results = results[:safe_limit]
    applied_filters = {
        "record_types": sorted(requested_types),
        "case_ids": sorted(requested_cases),
        "actors": sorted(requested_actors),
        "statuses": sorted(requested_statuses),
        "limit": safe_limit,
    }
    result_counts = Counter(item["record_type"] for item in results)
    facets = {
        name: dict(sorted(counter.items()))
        for name, counter in available_facets.items()
    }
    core = {"query": query, "applied_filters": applied_filters, "results": results}
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "query": query,
        "record_types": list(CORE_TYPES),
        "field_catalog": FIELD_CATALOG,
        "applied_filters": applied_filters,
        "facets": facets,
        "results": results,
        "result_count": len(results),
        "record_type_counts": dict(sorted(result_counts.items())),
        "visible_case_ids": sorted({item["case_id"] for item in results}),
        "search_sha256": _sha(core),
        "access_scope": {
            "mode": "restricted" if visible is not None else "all_visible_cases",
            "allowed_case_ids": sorted(visible) if visible is not None else None,
        },
        "read_only": True,
        "source_records_mutated": False,
        "search_record_created": False,
        "case_access_scope_changed": False,
        "relevance_is_not_confidence": True,
        "next_action": "refine_core_record_search"
        if query
        else "enter_case_entity_evidence_or_finding_query",
    }
