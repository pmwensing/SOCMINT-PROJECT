from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from .v10_29_final_delivery_dashboard_api import build_final_delivery_dashboard_api_from_request

CASE_DELIVERY_REGISTRY_SCHEMA = "socmint.v10_30.case_delivery_registry"
CASE_DELIVERY_ENTRY_SCHEMA = "socmint.v10_30.case_delivery_registry.entry"
CASE_DELIVERY_SUMMARY_SCHEMA = "socmint.v10_30.case_delivery_registry.summary"
VERSION = "v10.30.0"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def delivery_id_for_dashboard(case_id: str, dashboard: dict[str, Any]) -> str:
    core = {
        "case_id": case_id,
        "pack_id": dashboard.get("pack_id"),
        "capsule_id": dashboard.get("capsule_id"),
        "readiness": dashboard.get("readiness"),
        "bundle_name": dashboard.get("bundle_name"),
    }
    return sha256_text(canonical_json(core))


def build_delivery_entry(case_id: str, dashboard: dict[str, Any]) -> dict[str, Any]:
    safe_dashboard = deepcopy(dashboard or {})
    return {
        "schema": CASE_DELIVERY_ENTRY_SCHEMA,
        "version": VERSION,
        "delivery_id": delivery_id_for_dashboard(case_id, safe_dashboard),
        "case_id": case_id,
        "readiness": safe_dashboard.get("readiness"),
        "bundle_name": safe_dashboard.get("bundle_name"),
        "pack_id": safe_dashboard.get("pack_id"),
        "capsule_id": safe_dashboard.get("capsule_id"),
        "registered_at": utc_now(),
        "dashboard": safe_dashboard,
    }


def summarize_delivery_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": CASE_DELIVERY_SUMMARY_SCHEMA,
        "version": VERSION,
        "delivery_id": entry.get("delivery_id"),
        "case_id": entry.get("case_id"),
        "readiness": entry.get("readiness"),
        "bundle_name": entry.get("bundle_name"),
        "pack_id": entry.get("pack_id"),
        "capsule_id": entry.get("capsule_id"),
        "registered_at": entry.get("registered_at"),
    }


def list_delivery_summaries(registry: dict[str, Any]) -> list[dict[str, Any]]:
    deliveries = registry.get("deliveries") if isinstance(registry.get("deliveries"), list) else []
    return [summarize_delivery_entry(entry) for entry in deliveries if isinstance(entry, dict)]


def get_delivery_by_id(registry: dict[str, Any], delivery_id: str | None) -> dict[str, Any] | None:
    if not delivery_id:
        return None
    deliveries = registry.get("deliveries") if isinstance(registry.get("deliveries"), list) else []
    for entry in deliveries:
        if isinstance(entry, dict) and entry.get("delivery_id") == delivery_id:
            return deepcopy(entry)
    return None


def _summary(case_id: str, deliveries: list[dict[str, Any]]) -> dict[str, Any]:
    latest = deliveries[-1] if deliveries else {}
    readiness_counts: dict[str, int] = {}
    for entry in deliveries:
        readiness = str(entry.get("readiness") or "unknown")
        readiness_counts[readiness] = readiness_counts.get(readiness, 0) + 1
    return {
        "schema": CASE_DELIVERY_SUMMARY_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "delivery_count": len(deliveries),
        "latest_readiness": latest.get("readiness") if latest else None,
        "latest_delivery_id": latest.get("delivery_id") if latest else None,
        "readiness_counts": readiness_counts,
    }


def build_case_delivery_registry(case_id: str, dashboards: list[dict[str, Any]]) -> dict[str, Any]:
    safe_dashboards = [deepcopy(item) for item in dashboards if isinstance(item, dict)]
    deliveries = [build_delivery_entry(case_id, dashboard) for dashboard in safe_dashboards]
    summary = _summary(case_id, deliveries)
    return {
        "schema": CASE_DELIVERY_REGISTRY_SCHEMA,
        "version": VERSION,
        "case_id": case_id,
        "delivery_count": len(deliveries),
        "latest_readiness": summary.get("latest_readiness"),
        "latest_delivery_id": summary.get("latest_delivery_id"),
        "deliveries": deliveries,
        "summary": summary,
    }


def _dashboards_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    safe_payload = deepcopy(payload or {})
    if isinstance(safe_payload.get("dashboards"), list):
        return [item for item in safe_payload["dashboards"] if isinstance(item, dict)]
    if isinstance(safe_payload.get("dashboard"), dict):
        return [safe_payload["dashboard"]]
    return [build_final_delivery_dashboard_api_from_request(safe_payload)]


def build_case_delivery_registry_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return build_case_delivery_registry(case_id, _dashboards_from_payload(payload))


def build_case_delivery_summaries_from_request(case_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list_delivery_summaries(build_case_delivery_registry_from_request(case_id, payload))


def get_case_delivery_from_request(case_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    safe_payload = deepcopy(payload or {})
    registry = build_case_delivery_registry_from_request(case_id, safe_payload)
    return get_delivery_by_id(registry, safe_payload.get("delivery_id"))
