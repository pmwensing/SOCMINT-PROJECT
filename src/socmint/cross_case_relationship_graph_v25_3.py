from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .cross_case_confirmed_link_registry_v25_2 import confirmed_link_registry
from .dossier_assembly_workspace_v21_0 import _sha

SCHEMA = "socmint.cross_case_relationship_graph.v25_3"
VERSION = "v25.3.0"

NODE_TYPES = {
    "case",
    "entity",
    "identifier",
    "infrastructure",
    "evidence",
    "temporal",
}


def _node_id(node_type: str, value: str) -> str:
    return f"{node_type}-{_sha({'type': node_type, 'value': value})[:24]}"


def _edge_id(
    edge_type: str,
    source: str,
    target: str,
    link_id: str,
    occurrence_hash: str | None = None,
) -> str:
    return f"edge-{_sha({'type': edge_type, 'source': source, 'target': target, 'link': link_id, 'occurrence': occurrence_hash})[:24]}"


def _merge_unique(existing: list[Any], values: list[Any]) -> list[Any]:
    seen = {_sha(value) for value in existing}
    merged = list(existing)
    for value in values:
        digest = _sha(value)
        if digest not in seen:
            seen.add(digest)
            merged.append(value)
    return merged


def build_cross_case_relationship_graph(
    *,
    allowed_case_ids: set[str] | None = None,
    links: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    confirmed_links = links if links is not None else confirmed_link_registry(
        allowed_case_ids=allowed_case_ids
    )

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    projected_link_ids: set[str] = set()

    def add_node(
        node_type: str,
        value: str,
        *,
        label: str,
        link: dict[str, Any],
        occurrences: list[dict[str, Any]],
    ) -> str:
        node_id = _node_id(node_type, value)
        access_scope = link.get("accepted_review", {}).get("workspace_access_scope")
        provenance = {
            "confirmed_link_id": link.get("confirmed_link_id"),
            "confirmed_link_sha256": link.get("confirmed_link_sha256"),
            "accepted_review_decision_id": link.get("accepted_review_decision_id"),
            "accepted_review_decision_sha256": link.get("accepted_review_decision_sha256"),
            "registry_record_id": link.get("registry_record_id"),
            "registered_at": link.get("registered_at"),
            "registered_by": link.get("registered_by"),
            "source_occurrences_sha256": link.get("source_occurrences_sha256"),
            "access_scope": access_scope,
        }
        review_binding = {
            "decision_id": link.get("accepted_review_decision_id"),
            "decision_sha256": link.get("accepted_review_decision_sha256"),
        }
        existing = nodes.get(node_id)
        if existing is None:
            content = {
                "node_id": node_id,
                "node_type": node_type,
                "value": value,
                "label": label,
                "confirmed_link_ids": [link.get("confirmed_link_id")],
                "review_bindings": [review_binding],
                "access_scopes": [access_scope],
                "source_occurrences": occurrences,
                "provenance": [provenance],
            }
            content["node_sha256"] = _sha(content)
            nodes[node_id] = content
        else:
            existing["confirmed_link_ids"] = sorted(
                set(existing["confirmed_link_ids"] + [link.get("confirmed_link_id")])
            )
            existing["review_bindings"] = _merge_unique(
                existing["review_bindings"], [review_binding]
            )
            existing["access_scopes"] = _merge_unique(
                existing["access_scopes"], [access_scope]
            )
            existing["source_occurrences"] = _merge_unique(
                existing["source_occurrences"], occurrences
            )
            existing["provenance"] = _merge_unique(
                existing["provenance"], [provenance]
            )
            recalculated = {
                key: item for key, item in existing.items() if key != "node_sha256"
            }
            existing["node_sha256"] = _sha(recalculated)
        return node_id

    def add_edge(
        edge_type: str,
        source: str,
        target: str,
        *,
        link: dict[str, Any],
        occurrences: list[dict[str, Any]],
        occurrence_hash: str | None = None,
    ) -> None:
        edge_id = _edge_id(
            edge_type,
            source,
            target,
            str(link.get("confirmed_link_id")),
            occurrence_hash,
        )
        content = {
            "edge_id": edge_id,
            "edge_type": edge_type,
            "source": source,
            "target": target,
            "confirmed_link_id": link.get("confirmed_link_id"),
            "confirmed_link_sha256": link.get("confirmed_link_sha256"),
            "accepted_review_decision_id": link.get("accepted_review_decision_id"),
            "accepted_review_decision_sha256": link.get("accepted_review_decision_sha256"),
            "source_occurrences": occurrences,
            "source_occurrences_sha256": _sha(occurrences),
            "access_scope": link.get("accepted_review", {}).get(
                "workspace_access_scope"
            ),
            "provenance": {
                "registry_record_id": link.get("registry_record_id"),
                "registered_at": link.get("registered_at"),
                "registered_by": link.get("registered_by"),
                "source_occurrences_sha256": link.get(
                    "source_occurrences_sha256"
                ),
            },
        }
        content["edge_sha256"] = _sha(content)
        edges[edge_id] = content

    for link in confirmed_links:
        case_ids = sorted(
            {str(value) for value in link.get("case_ids") or [] if str(value)}
        )
        if allowed_case_ids is not None and any(
            case_id not in allowed_case_ids for case_id in case_ids
        ):
            continue

        link_id = str(link.get("confirmed_link_id") or "").strip()
        if not link_id:
            continue
        projected_link_ids.add(link_id)

        category = str(link.get("category") or "").strip().lower()
        graph_type = (
            category
            if category in {"entity", "identifier", "infrastructure", "evidence"}
            else "temporal"
        )
        value = str(
            link.get("match_value") or link.get("confirmed_link_id") or "unknown"
        )
        label = " / ".join(
            str(item) for item in link.get("display_values") or [value]
        )
        occurrences = list(link.get("source_occurrences") or [])

        value_node = add_node(
            graph_type,
            value,
            label=label,
            link=link,
            occurrences=occurrences,
        )

        by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for occurrence in occurrences:
            case_id = str(occurrence.get("case_id") or "").strip()
            if case_id:
                by_case[case_id].append(occurrence)

        for case_id in case_ids:
            case_occurrences = sorted(
                by_case.get(case_id, []),
                key=lambda item: (
                    item.get("occurred_at") or "",
                    int(item.get("record_id") or 0),
                    item.get("field_path") or "",
                ),
            )
            case_node = add_node(
                "case",
                case_id,
                label=case_id,
                link=link,
                occurrences=case_occurrences,
            )
            add_edge(
                "case_confirmed_link",
                case_node,
                value_node,
                link=link,
                occurrences=case_occurrences,
            )

            for occurrence in case_occurrences:
                occurred_at = str(occurrence.get("occurred_at") or "").strip()
                if not occurred_at:
                    continue
                temporal_node = add_node(
                    "temporal",
                    occurred_at,
                    label=occurred_at,
                    link=link,
                    occurrences=[occurrence],
                )
                occurrence_hash = str(
                    occurrence.get("provenance_sha256") or _sha(occurrence)
                )
                add_edge(
                    "case_observed_at",
                    case_node,
                    temporal_node,
                    link=link,
                    occurrences=[occurrence],
                    occurrence_hash=occurrence_hash,
                )
                add_edge(
                    "linked_value_observed_at",
                    value_node,
                    temporal_node,
                    link=link,
                    occurrences=[occurrence],
                    occurrence_hash=occurrence_hash,
                )

    node_list = sorted(
        nodes.values(),
        key=lambda item: (item["node_type"], item["label"], item["node_id"]),
    )
    edge_list = sorted(
        edges.values(),
        key=lambda item: (
            item["edge_type"],
            item["source"],
            item["target"],
            item["edge_id"],
        ),
    )
    node_counts = Counter(item["node_type"] for item in node_list)
    edge_counts = Counter(item["edge_type"] for item in edge_list)

    graph_core = {
        "nodes": node_list,
        "edges": edge_list,
        "confirmed_link_ids": sorted(projected_link_ids),
    }

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "access_scope": {
            "mode": "restricted"
            if allowed_case_ids is not None
            else "all_visible_cases",
            "allowed_case_ids": sorted(allowed_case_ids)
            if allowed_case_ids is not None
            else None,
        },
        "graph": graph_core,
        "graph_sha256": _sha(graph_core),
        "counts": {
            "confirmed_links": len(graph_core["confirmed_link_ids"]),
            "nodes": len(node_list),
            "edges": len(edge_list),
            "nodes_by_type": dict(sorted(node_counts.items())),
            "edges_by_type": dict(sorted(edge_counts.items())),
        },
        "node_types": sorted(NODE_TYPES),
        "source_occurrences_preserved": True,
        "review_bindings_preserved": True,
        "access_scope_preserved": True,
        "provenance_preserved": True,
        "source_records_mutated": False,
        "graph_record_created": False,
        "next_action": "review_cross_case_relationship_graph",
    }
