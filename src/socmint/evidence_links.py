
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .evidence_intake import evidence_root
from .evidence_intake import list_evidence
from .report_export_center import safe_export_artifact_path
from .evidence_custody import record_custody_event


@dataclass
class EvidenceLink:
    link_id: str
    evidence_id: str
    review_item_id: str
    relation: str
    confidence: float | None
    note: str | None
    created_at: str
    created_by: str | None = None


VALID_RELATIONS = {
    "supports",
    "contradicts",
    "source",
    "context",
    "attachment",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def link_manifest_path() -> Path:
    evidence_root().mkdir(parents=True, exist_ok=True)
    return evidence_root() / "EVIDENCE-LINKS.json"


def _load_links() -> list[dict[str, Any]]:
    path = link_manifest_path()

    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(errors="replace"))
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        return list(payload.get("links") or [])

    if isinstance(payload, list):
        return payload

    return []


def _write_links(links: list[dict[str, Any]]) -> None:
    payload = {
        "schema": "socmint.evidence_links.v7_4_1",
        "generated_at": utc_now(),
        "count": len(links),
        "links": links,
    }
    link_manifest_path().write_text(json.dumps(payload, indent=2, sort_keys=True))


def _make_link_id(evidence_id: str, review_item_id: str, relation: str) -> str:
    safe_item = review_item_id.replace(":", "_").replace("/", "_")
    return f"{evidence_id[:16]}-{safe_item}-{relation}"


def link_evidence_to_review_item(
    evidence_id: str,
    review_item_id: str,
    relation: str = "supports",
    confidence: float | None = None,
    note: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    if relation not in VALID_RELATIONS:
        raise ValueError(f"Invalid evidence relation: {relation}")

    if not evidence_id:
        raise ValueError("evidence_id required")

    if not review_item_id:
        raise ValueError("review_item_id required")

    link = EvidenceLink(
        link_id=_make_link_id(evidence_id, review_item_id, relation),
        evidence_id=evidence_id,
        review_item_id=review_item_id,
        relation=relation,
        confidence=confidence,
        note=note,
        created_at=utc_now(),
        created_by=created_by,
    )

    links = _load_links()

    links = [
        item
        for item in links
        if not (
            item.get("evidence_id") == evidence_id
            and item.get("review_item_id") == review_item_id
            and item.get("relation") == relation
        )
    ]
    links.append(asdict(link))
    _write_links(links)

    record_custody_event(
        evidence_id=evidence_id,
        action="link",
        actor=created_by,
        status="linked",
        note=note,
        details={
            "review_item_id": review_item_id,
            "relation": relation,
            "confidence": confidence,
        },
    )

    return asdict(link)


def unlink_evidence_from_review_item(
    evidence_id: str,
    review_item_id: str,
    relation: str | None = None,
) -> dict[str, Any]:
    links = _load_links()
    before = len(links)

    def keep(item: dict[str, Any]) -> bool:
        same_pair = (
            item.get("evidence_id") == evidence_id
            and item.get("review_item_id") == review_item_id
        )
        if not same_pair:
            return True
        if relation is None:
            return False
        return item.get("relation") != relation

    links = [item for item in links if keep(item)]
    _write_links(links)

    if before - len(links) > 0:
        record_custody_event(
            evidence_id=evidence_id,
            action="unlink",
            actor=None,
            status="unlinked",
            note="evidence link removed",
            details={
                "review_item_id": review_item_id,
                "relation": relation,
                "removed": before - len(links),
            },
        )

    return {
        "schema": "socmint.evidence_unlink_result.v7_4_1",
        "removed": before - len(links),
        "remaining": len(links),
        "evidence_id": evidence_id,
        "review_item_id": review_item_id,
        "relation": relation,
    }


def list_evidence_links(
    review_item_id: str | None = None,
    evidence_id: str | None = None,
) -> list[dict[str, Any]]:
    links = _load_links()

    if review_item_id:
        links = [
            item
            for item in links
            if item.get("review_item_id") == review_item_id
        ]

    if evidence_id:
        links = [
            item
            for item in links
            if item.get("evidence_id") == evidence_id
        ]

    return links


def evidence_links_payload(
    review_item_id: str | None = None,
    evidence_id: str | None = None,
) -> dict[str, Any]:
    links = list_evidence_links(
        review_item_id=review_item_id,
        evidence_id=evidence_id,
    )
    evidence = list_evidence()

    by_id = {
        item.get("evidence_id"): item
        for item in evidence
        if item.get("evidence_id")
    }

    enriched = []
    for link in links:
        item = dict(link)
        item["evidence"] = by_id.get(link.get("evidence_id"))
        enriched.append(item)

    return {
        "schema": "socmint.evidence_links_payload.v7_4_1",
        "generated_at": utc_now(),
        "count": len(enriched),
        "links": enriched,
        "evidence_count": len(evidence),
        "evidence": evidence,
        "relations": sorted(VALID_RELATIONS),
    }


def linked_evidence_for_review_items(
    review_item_ids: list[str],
) -> list[dict[str, Any]]:
    evidence = list_evidence()
    by_id = {
        item.get("evidence_id"): item
        for item in evidence
        if item.get("evidence_id")
    }

    wanted = set(review_item_ids)
    linked = []

    for link in _load_links():
        if link.get("review_item_id") not in wanted:
            continue

        evidence_item = by_id.get(link.get("evidence_id"))
        if not evidence_item:
            continue

        merged = dict(evidence_item)
        merged["link"] = link
        linked.append(merged)

    deduped = []
    seen = set()
    for item in linked:
        key = item.get("sha256") or item.get("evidence_id")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def linked_evidence_for_export_manifest(
    export_manifest_name: str,
) -> list[dict[str, Any]]:
    path = safe_export_artifact_path(export_manifest_name)
    payload = json.loads(path.read_text(errors="replace"))

    included_ids = [
        str(item.get("id"))
        for item in payload.get("included_items") or []
        if item.get("id")
    ]

    return linked_evidence_for_review_items(included_ids)


def review_item_attachment_map(
    export_manifest_name: str | None = None,
) -> dict[str, Any]:
    links = _load_links()
    evidence = list_evidence()

    evidence_by_id = {
        item.get("evidence_id"): item
        for item in evidence
        if item.get("evidence_id")
    }

    export_item_ids: set[str] | None = None
    export_id = None

    if export_manifest_name:
        path = safe_export_artifact_path(export_manifest_name)
        payload = json.loads(path.read_text(errors="replace"))
        export_id = payload.get("export_id")
        export_item_ids = {
            str(item.get("id"))
            for item in payload.get("included_items") or []
            if item.get("id")
        }

    mapped: dict[str, list[dict[str, Any]]] = {}

    for link in links:
        review_item_id = str(link.get("review_item_id"))

        if export_item_ids is not None and review_item_id not in export_item_ids:
            continue

        evidence_item = evidence_by_id.get(link.get("evidence_id"))
        entry = {
            "link": link,
            "evidence": evidence_item,
        }
        mapped.setdefault(review_item_id, []).append(entry)

    return {
        "schema": "socmint.review_item_attachment_map.v7_4_1",
        "generated_at": utc_now(),
        "export_id": export_id,
        "export_manifest_name": export_manifest_name,
        "review_item_count": len(mapped),
        "attachment_count": sum(len(items) for items in mapped.values()),
        "items": mapped,
    }
