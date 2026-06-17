from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from .core_record_search_v27_1 import build_core_record_search
from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.advanced_search_filters.v27_2"
VERSION = "v27.2.0"
SORT_MODES = ("relevance", "newest", "oldest", "case", "type", "actor")


def _values(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    return {item.strip() for item in str(value).split(",") if item.strip()}


def _date(value: str | None, *, end: bool = False) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if len(text) == 10:
            stamp = datetime.fromisoformat(text)
            if end:
                stamp = stamp.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc)
    except ValueError:
        return None


def _occurred(item: dict[str, Any]) -> datetime | None:
    return _date(item.get("occurred_at"))


def _preview_map(item: dict[str, Any]) -> dict[str, str]:
    fields = (item.get("preview") or {}).get("fields") or []
    return {str(field.get("field")): str(field.get("value") or "") for field in fields}


def _search_text(item: dict[str, Any]) -> str:
    parts = [
        item.get("case_id"), item.get("record_type"), item.get("actor"), item.get("status"),
        item.get("source_action"), *(item.get("matched_terms") or []),
    ]
    parts.extend(_preview_map(item).values())
    return " ".join(str(part or "") for part in parts).lower()


def _facet_value(item: dict[str, Any], name: str) -> str:
    preview = _preview_map(item)
    if name == "stage":
        return preview.get("stage") or (item.get("status") if item.get("record_type") == "case" else "unspecified")
    if name == "confidence":
        return preview.get("confidence") or "unspecified"
    if name == "priority":
        return preview.get("priority") or "unspecified"
    if name == "source_action":
        return str(item.get("source_action") or "unspecified")
    return str(item.get(name) or "unspecified")


def _exact_matches(item: dict[str, Any], constraints: dict[str, str]) -> bool:
    preview = _preview_map(item)
    direct = {
        "case_id": str(item.get("case_id") or ""),
        "record_type": str(item.get("record_type") or ""),
        "actor": str(item.get("actor") or ""),
        "status": str(item.get("status") or ""),
        "source_action": str(item.get("source_action") or ""),
    }
    for field, expected in constraints.items():
        actual = direct.get(field, preview.get(field, ""))
        if actual.lower() != str(expected).strip().lower():
            return False
    return True


def _sort(results: list[dict[str, Any]], mode: str) -> None:
    if mode == "newest":
        results.sort(key=lambda item: (item.get("occurred_at") or "", item.get("score") or 0, item.get("result_id") or ""), reverse=True)
    elif mode == "oldest":
        results.sort(key=lambda item: (item.get("occurred_at") or "9999", -(item.get("score") or 0), item.get("result_id") or ""))
    elif mode == "case":
        results.sort(key=lambda item: (item.get("case_id") or "", -(item.get("score") or 0), item.get("result_id") or ""))
    elif mode == "type":
        results.sort(key=lambda item: (item.get("record_type") or "", -(item.get("score") or 0), item.get("result_id") or ""))
    elif mode == "actor":
        results.sort(key=lambda item: (item.get("actor") or "", -(item.get("score") or 0), item.get("result_id") or ""))
    else:
        results.sort(key=lambda item: (item.get("score") or 0, item.get("occurred_at") or "", item.get("result_id") or ""), reverse=True)


def build_advanced_search_filters(
    query: str = "",
    *,
    record_types: Any = None,
    case_ids: Any = None,
    actors: Any = None,
    statuses: Any = None,
    stages: Any = None,
    source_actions: Any = None,
    confidences: Any = None,
    priorities: Any = None,
    date_from: str | None = None,
    date_to: str | None = None,
    include_terms: Any = None,
    exclude_terms: Any = None,
    exact_fields: dict[str, str] | None = None,
    sort: str = "relevance",
    allowed_case_ids: set[str] | None = None,
    limit: int = 100,
    base_payload: dict[str, Any] | None = None,
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sort_mode = sort if sort in SORT_MODES else "relevance"
    safe_limit = max(1, min(int(limit or 100), 500))
    base = base_payload or build_core_record_search(
        query,
        record_types=list(_values(record_types)),
        case_ids=list(_values(case_ids)),
        actors=list(_values(actors)),
        statuses=list(_values(statuses)),
        allowed_case_ids=allowed_case_ids,
        limit=500,
        records=records,
    )
    candidates = list(base.get("results") or [])
    stage_set = _values(stages)
    action_set = _values(source_actions)
    confidence_set = _values(confidences)
    priority_set = _values(priorities)
    includes = {item.lower() for item in _values(include_terms)}
    excludes = {item.lower() for item in _values(exclude_terms)}
    constraints = {str(key): str(value) for key, value in (exact_fields or {}).items() if str(key) and str(value)}
    start = _date(date_from)
    end = _date(date_to, end=True)

    facet_source = defaultdict(Counter)
    for item in candidates:
        for name in ("record_type", "case_id", "actor", "status", "stage", "source_action", "confidence", "priority"):
            facet_source[name][_facet_value(item, name)] += 1

    results = []
    excluded_counts = Counter()
    for item in candidates:
        if stage_set and _facet_value(item, "stage") not in stage_set:
            excluded_counts["stage"] += 1
            continue
        if action_set and _facet_value(item, "source_action") not in action_set:
            excluded_counts["source_action"] += 1
            continue
        if confidence_set and _facet_value(item, "confidence") not in confidence_set:
            excluded_counts["confidence"] += 1
            continue
        if priority_set and _facet_value(item, "priority") not in priority_set:
            excluded_counts["priority"] += 1
            continue
        occurred = _occurred(item)
        if start and (occurred is None or occurred < start):
            excluded_counts["before_date_from"] += 1
            continue
        if end and (occurred is None or occurred > end):
            excluded_counts["after_date_to"] += 1
            continue
        text = _search_text(item)
        if includes and not all(term in text for term in includes):
            excluded_counts["include_terms"] += 1
            continue
        if excludes and any(term in text for term in excludes):
            excluded_counts["exclude_terms"] += 1
            continue
        if constraints and not _exact_matches(item, constraints):
            excluded_counts["exact_fields"] += 1
            continue
        results.append(item)

    _sort(results, sort_mode)
    results = results[:safe_limit]
    active_filters = {
        "record_types": sorted(_values(record_types)),
        "case_ids": sorted(_values(case_ids)),
        "actors": sorted(_values(actors)),
        "statuses": sorted(_values(statuses)),
        "stages": sorted(stage_set),
        "source_actions": sorted(action_set),
        "confidences": sorted(confidence_set),
        "priorities": sorted(priority_set),
        "date_from": str(date_from or ""),
        "date_to": str(date_to or ""),
        "include_terms": sorted(includes),
        "exclude_terms": sorted(excludes),
        "exact_fields": dict(sorted(constraints.items())),
        "sort": sort_mode,
        "limit": safe_limit,
    }
    applied_filter_count = sum(
        bool(value) for key, value in active_filters.items() if key not in {"sort", "limit"}
    )
    facets = {name: dict(sorted(values.items())) for name, values in facet_source.items()}
    filtered_facets = defaultdict(Counter)
    for item in results:
        for name in facets:
            filtered_facets[name][_facet_value(item, name)] += 1
    core = {"query": query, "active_filters": active_filters, "result_ids": [item.get("result_id") for item in results]}
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "query": str(query or ""),
        "sort_modes": list(SORT_MODES),
        "active_filters": active_filters,
        "active_filter_count": applied_filter_count,
        "facets": facets,
        "filtered_facets": {name: dict(sorted(values.items())) for name, values in filtered_facets.items()},
        "excluded_counts": dict(sorted(excluded_counts.items())),
        "candidate_count": len(candidates),
        "result_count": len(results),
        "results": results,
        "filter_sha256": _sha(active_filters),
        "result_set_sha256": _sha(core),
        "access_scope": base.get("access_scope"),
        "read_only": True,
        "source_records_mutated": False,
        "filter_record_created": False,
        "case_access_scope_changed": False,
        "relevance_is_not_confidence": True,
        "next_action": "review_filtered_results" if results else "broaden_advanced_filters",
    }
