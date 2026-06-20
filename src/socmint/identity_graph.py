import json
from collections import defaultdict
from urllib.parse import urlparse

from . import database as db


ENTITY_TYPE_MAP = {
    "account_presence": "account",
    "archive_candidate": "url",
    "seed_expansion_candidate": "identifier",
    "email": "email",
    "phone": "phone",
    "username": "username",
    "url": "url",
}


def _json_loads(value, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return default


def normalize_entity_value(entity_type, value):
    raw = str(value or "").strip()
    if entity_type in {"email", "username", "domain"}:
        return raw.lower()
    if entity_type == "url" or raw.startswith(("http://", "https://")):
        parsed = urlparse(raw)
        if parsed.scheme and parsed.netloc:
            path = parsed.path.rstrip("/")
            return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
    return raw.lower() if entity_type != "account" else raw


def infer_entity_type(observation):
    value = observation.normalized_value or ""
    obs_type = observation.observation_type or ""
    if value.startswith(("http://", "https://")):
        return "url" if obs_type == "archive_candidate" else "account"
    return ENTITY_TYPE_MAP.get(obs_type, "identifier")


def build_identity_graph(subject_id):
    subject = db.get_spine_subject(subject_id)
    if not subject:
        raise ValueError("Subject not found.")

    graph_id = db.create_identity_graph(subject_id=subject_id, label=subject.label)

    seed_nodes = {}
    for seed in db.list_spine_seeds(subject_id):
        node_id = db.upsert_identity_node(
            graph_id=graph_id,
            entity_type=seed.seed_type,
            normalized_value=seed.normalized_value,
            display_value=seed.normalized_value,
            confidence="1.0",
            payload={
                "source": "seed",
                "seed_id": seed.id,
                "pii_hash": seed.pii_hash,
            },
        )
        seed_nodes[seed.seed_type] = node_id

    for obs in db.list_spine_observations(subject_id):
        entity_type = infer_entity_type(obs)
        normalized = normalize_entity_value(entity_type, obs.normalized_value)
        node_id = db.upsert_identity_node(
            graph_id=graph_id,
            entity_type=entity_type,
            normalized_value=normalized,
            display_value=obs.normalized_value,
            confidence=str(obs.confidence or "0.5"),
            payload={
                "source": "observation",
                "observation_id": obs.id,
                "source_ref": obs.source_ref,
                "evidence_ref": obs.evidence_ref,
                "observation_type": obs.observation_type,
                "payload": _json_loads(obs.payload_json),
            },
        )

        seed_node_id = seed_nodes.get(
            _json_loads(obs.payload_json).get("seed_type", "")
        )
        if seed_node_id:
            db.upsert_identity_edge(
                graph_id=graph_id,
                from_node_id=seed_node_id,
                to_node_id=node_id,
                edge_type="expanded_to",
                confidence=str(obs.confidence or "0.5"),
                evidence_ref=obs.evidence_ref,
                payload={"observation_id": obs.id, "source_ref": obs.source_ref},
            )

    create_merge_candidates(graph_id)
    return graph_id


def create_merge_candidates(graph_id):
    nodes = db.list_identity_nodes(graph_id)
    grouped = defaultdict(list)

    for node in nodes:
        key = (node.entity_type, node.normalized_value)
        grouped[key].append(node)

    candidate_ids = []
    for (entity_type, normalized_value), group in grouped.items():
        if len(group) < 2:
            continue
        candidate_ids.append(
            db.create_identity_merge_candidate(
                graph_id=graph_id,
                entity_type=entity_type,
                normalized_value=normalized_value,
                node_ids=[node.id for node in group],
                confidence="0.75",
                reason="Duplicate normalized entity value.",
            )
        )

    return candidate_ids


def graph_payload(subject_id):
    graph = db.get_latest_identity_graph(subject_id)
    if not graph:
        graph_id = build_identity_graph(subject_id)
        graph = db.get_identity_graph(graph_id)

    nodes = db.list_identity_nodes(graph.id)
    edges = db.list_identity_edges(graph.id)
    candidates = db.list_identity_merge_candidates(graph.id)

    return {
        "graph": {
            "id": graph.id,
            "subject_id": graph.subject_id,
            "label": graph.label,
            "created_at": graph.created_at.isoformat() if graph.created_at else None,
        },
        "nodes": [
            {
                "id": node.id,
                "type": node.entity_type,
                "value": node.normalized_value,
                "display": node.display_value,
                "confidence": float(node.confidence or 0),
                "validation_state": node.validation_state,
                "payload": _json_loads(node.payload_json),
            }
            for node in nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "from": edge.from_node_id,
                "to": edge.to_node_id,
                "type": edge.edge_type,
                "confidence": float(edge.confidence or 0),
                "evidence_ref": edge.evidence_ref,
                "validation_state": edge.validation_state,
                "payload": _json_loads(edge.payload_json),
            }
            for edge in edges
        ],
        "merge_candidates": [
            {
                "id": item.id,
                "type": item.entity_type,
                "value": item.normalized_value,
                "node_ids": _json_loads(item.node_ids_json, []),
                "confidence": float(item.confidence or 0),
                "state": item.state,
                "reason": item.reason,
            }
            for item in candidates
        ],
    }


def apply_merge_candidate(candidate_id, action, actor=None, note=None):
    if action not in {"merged", "rejected", "unreviewed"}:
        raise ValueError("Invalid merge candidate action.")
    return db.update_identity_merge_candidate(
        candidate_id=candidate_id,
        state=action,
        actor=actor,
        note=note,
    )
