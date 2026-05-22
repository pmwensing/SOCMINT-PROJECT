from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

SCHEMA = "socmint.entity_alias_graph.v12_10_6"
PIPELINE_STAGE = "entity_alias_graph"
ALIAS_TYPES = {"email", "username", "phone", "url", "domain", "handle", "visual_hash", "text_hash"}
CONFIRMED_STATES = {"confirmed", "accepted"}
REJECTED_STATES = {"rejected", "suppressed"}
UNCERTAIN_STATES = {"uncertain", "needs_more_evidence", "unreviewed", "candidate"}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _norm(value).lower()


def _sha(value: Any) -> str:
    return hashlib.sha256(_norm(value).encode()).hexdigest()[:20]


def _domain(url: str) -> str:
    value = _norm(url)
    parsed = urlparse(value)
    return (parsed.netloc or parsed.path.split("/", 1)[0]).lower().removeprefix("www.")


def normalize_alias(alias_type: str, value: Any) -> str:
    value_s = _norm(value)
    if alias_type in {"email", "username", "handle", "domain", "url"}:
        value_s = value_s.lower()
    if alias_type == "handle":
        value_s = value_s.lstrip("@")
    if alias_type == "username":
        value_s = value_s.lstrip("@")
    if alias_type == "phone":
        digits = re.sub(r"\D+", "", value_s)
        return digits or value_s
    if alias_type == "domain":
        return _domain(value_s) if "://" in value_s or "/" in value_s else value_s.removeprefix("www.")
    return value_s


@dataclass
class AliasEvidence:
    source: str
    source_ref: str | None = None
    evidence_ref: str | None = None
    candidate_id: str | None = None
    confidence: float = 0.5
    reason: str = "observed"
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EntityAlias:
    alias_id: str
    alias_type: str
    alias_value: str
    normalized_value: str
    confidence: float
    analyst_state: str = "candidate"
    source_connectors: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    candidate_ids: list[str] = field(default_factory=list)
    evidence: list[AliasEvidence] = field(default_factory=list)

    def add_evidence(self, ev: AliasEvidence) -> None:
        self.evidence.append(ev)
        if ev.source and ev.source not in self.source_connectors:
            self.source_connectors.append(ev.source)
        if ev.evidence_ref and ev.evidence_ref not in self.evidence_refs:
            self.evidence_refs.append(ev.evidence_ref)
        if ev.candidate_id and ev.candidate_id not in self.candidate_ids:
            self.candidate_ids.append(ev.candidate_id)
        self.confidence = round(max(self.confidence, min(0.99, sum(item.confidence for item in self.evidence) / max(1, len(self.evidence)) + min(0.15, len(self.source_connectors) * 0.03))), 3)

    def as_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["evidence"] = [item.as_dict() if hasattr(item, "as_dict") else item for item in self.evidence]
        return row


def _new_alias(alias_type: str, value: Any, confidence: float = 0.5, state: str = "candidate") -> EntityAlias:
    normalized = normalize_alias(alias_type, value)
    return EntityAlias(
        alias_id=f"alias-{alias_type}-{_sha(normalized)}",
        alias_type=alias_type,
        alias_value=_norm(value),
        normalized_value=normalized,
        confidence=round(float(confidence or 0.0), 3),
        analyst_state=state,
    )


def _add_alias(index: dict[tuple[str, str], EntityAlias], alias_type: str, value: Any, evidence: AliasEvidence, state: str = "candidate") -> None:
    normalized = normalize_alias(alias_type, value)
    if not normalized:
        return
    key = (alias_type, normalized)
    if key not in index:
        index[key] = _new_alias(alias_type, value, evidence.confidence, state)
    if state in CONFIRMED_STATES and index[key].analyst_state not in REJECTED_STATES:
        index[key].analyst_state = "confirmed"
    elif state in REJECTED_STATES:
        index[key].analyst_state = "rejected"
    index[key].add_evidence(evidence)


def _seed_aliases(payload: dict[str, Any], index: dict[tuple[str, str], EntityAlias]) -> None:
    for seed in payload.get("seeds", []) or []:
        stype = _lower(seed.get("type"))
        value = _norm(seed.get("value"))
        if not value:
            continue
        if stype not in ALIAS_TYPES:
            stype = "handle" if stype == "name" else stype
        if stype in ALIAS_TYPES:
            _add_alias(index, stype, value, AliasEvidence(source="seed", source_ref=f"seed:{seed.get('id')}", confidence=0.9, reason="subject seed", details=seed), state="confirmed")
        if stype == "email" and "@" in value:
            local, domain = value.split("@", 1)
            _add_alias(index, "username", local, AliasEvidence(source="seed", source_ref=f"seed:{seed.get('id')}", confidence=0.72, reason="email local-part alias candidate", details=seed), state="candidate")
            _add_alias(index, "domain", domain, AliasEvidence(source="seed", source_ref=f"seed:{seed.get('id')}", confidence=0.75, reason="email domain", details=seed), state="candidate")


def _observation_aliases(payload: dict[str, Any], index: dict[tuple[str, str], EntityAlias]) -> None:
    type_map = {"email": "email", "username": "username", "phone": "phone", "profile_url": "url", "external_url": "url", "domain": "domain", "account_presence": "handle", "platform_presence": "domain"}
    for obs in payload.get("observations", []) or []:
        otype = _lower(obs.get("type"))
        alias_type = type_map.get(otype)
        value = _norm(obs.get("value"))
        if not alias_type or not value:
            continue
        confidence = float(obs.get("confidence") or 0.45)
        connector = _norm(obs.get("connector") or _norm(obs.get("source_ref")).split(":")[-1] or "observation")
        _add_alias(index, alias_type, value, AliasEvidence(source=connector, source_ref=obs.get("source_ref"), evidence_ref=obs.get("evidence_ref"), confidence=confidence, reason="spine observation", details={"observation_id": obs.get("id"), "type": otype}), state="candidate")
        if alias_type == "url":
            dom = _domain(value)
            _add_alias(index, "domain", dom, AliasEvidence(source=connector, source_ref=obs.get("source_ref"), evidence_ref=obs.get("evidence_ref"), confidence=min(0.7, confidence), reason="domain derived from observed URL", details={"observation_id": obs.get("id")}), state="candidate")


def _candidate_evidence(candidate: dict[str, Any], fp: dict[str, Any], confidence: float, reason: str, field_name: str) -> AliasEvidence:
    source_connectors = fp.get("source_connectors") if isinstance(fp.get("source_connectors"), list) else []
    source = source_connectors[0] if source_connectors else candidate.get("source_connector") or "candidate_profile"
    return AliasEvidence(
        source=source,
        evidence_ref=(candidate.get("evidence_refs") or [None])[0],
        candidate_id=candidate.get("candidate_id"),
        confidence=round(float(confidence or 0.0), 3),
        reason=reason,
        details={"field": field_name, "collision_status": candidate.get("collision_status")},
    )


def _candidate_aliases(profile_payload: dict[str, Any], index: dict[tuple[str, str], EntityAlias]) -> None:
    for candidate in profile_payload.get("candidates", []) or []:
        fp = candidate.get("profile_fingerprint") or {}
        state = candidate.get("analyst_review", {}).get("review_state") or "candidate"
        if state == "accepted":
            alias_state = "confirmed"
        elif state == "rejected" or fp.get("asset_only_url") or candidate.get("dossier_assertion_gate", {}).get("suppressed"):
            alias_state = "rejected"
        elif state in {"uncertain", "needs_more_evidence"}:
            alias_state = state
        else:
            alias_state = "candidate"
        base_conf = float(candidate.get("identity_score") or 0.35)
        for alias_type, fp_field in (("username", "username"), ("url", "profile_url"), ("visual_hash", "avatar_phash"), ("visual_hash", "banner_phash"), ("visual_hash", "visual_fingerprint_hash"), ("text_hash", "text_fingerprint_hash")):
            if fp.get(fp_field):
                _add_alias(index, alias_type, fp.get(fp_field), _candidate_evidence(candidate, fp, base_conf, "candidate profile alias evidence", fp_field), state=alias_state)
        if fp.get("profile_url"):
            _add_alias(index, "domain", _domain(fp.get("profile_url")), _candidate_evidence(candidate, fp, base_conf, "domain derived from candidate profile URL", "profile_url_domain"), state=alias_state)
        for url in fp.get("linked_urls") or []:
            _add_alias(index, "url", url, _candidate_evidence(candidate, fp, max(0.2, base_conf - 0.1), "linked URL on candidate profile", "linked_urls"), state=alias_state)
            _add_alias(index, "domain", _domain(url), _candidate_evidence(candidate, fp, max(0.2, base_conf - 0.15), "domain derived from linked URL", "linked_urls_domain"), state=alias_state)


def _edges(aliases: list[EntityAlias]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    by_candidate: dict[str, list[EntityAlias]] = defaultdict(list)
    by_evidence: dict[str, list[EntityAlias]] = defaultdict(list)
    for alias in aliases:
        for cid in alias.candidate_ids:
            by_candidate[cid].append(alias)
        for ref in alias.evidence_refs:
            by_evidence[ref].append(alias)
    seen: set[tuple[str, str, str]] = set()
    def add_group_edges(group: dict[str, list[EntityAlias]], relation: str) -> None:
        for group_id, rows in group.items():
            ids = sorted({row.alias_id for row in rows})
            for i, left in enumerate(ids):
                for right in ids[i + 1:]:
                    key = (left, right, relation)
                    if key in seen:
                        continue
                    seen.add(key)
                    edges.append({"source": left, "target": right, "relation": relation, "group_id": group_id, "confidence": 0.55})
    add_group_edges(by_candidate, "same_candidate_profile")
    add_group_edges(by_evidence, "same_evidence_reference")
    return edges


def _collision_sets(aliases: list[EntityAlias]) -> list[dict[str, Any]]:
    collisions: list[dict[str, Any]] = []
    for alias in aliases:
        candidate_count = len(alias.candidate_ids)
        connector_count = len(alias.source_connectors)
        rejected = alias.analyst_state in REJECTED_STATES
        if candidate_count > 1 and alias.alias_type in {"username", "handle", "visual_hash", "url"}:
            collisions.append({"alias_id": alias.alias_id, "alias_type": alias.alias_type, "normalized_value": alias.normalized_value, "status": "reverse_collision_review", "candidate_count": candidate_count, "connector_count": connector_count, "reason": "one alias appears across multiple candidate profiles; review before merging identities"})
        elif rejected:
            collisions.append({"alias_id": alias.alias_id, "alias_type": alias.alias_type, "normalized_value": alias.normalized_value, "status": "rejected_or_suppressed", "candidate_count": candidate_count, "connector_count": connector_count, "reason": "alias is attached to a rejected or asset-only candidate"})
    return collisions


def build_entity_alias_graph(payload: dict[str, Any], profile_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    index: dict[tuple[str, str], EntityAlias] = {}
    _seed_aliases(payload, index)
    _observation_aliases(payload, index)
    if profile_payload:
        _candidate_aliases(profile_payload, index)
    aliases = sorted(index.values(), key=lambda item: (item.alias_type, item.normalized_value))
    rows = [alias.as_dict() for alias in aliases]
    counts = Counter(alias.analyst_state for alias in aliases)
    type_counts = Counter(alias.alias_type for alias in aliases)
    edges = _edges(aliases)
    collisions = _collision_sets(aliases)
    return {
        "schema": SCHEMA,
        "stage": PIPELINE_STAGE,
        "subject_id": payload.get("subject", {}).get("id"),
        "pipeline_insert": "Connector Finding → Candidate Identifier → Alias Evidence → Entity Alias Graph → Candidate Profile → Profile Fingerprint → Collision Resolver → Identity Link Hypothesis → Analyst Review → Dossier Assertion",
        "alias_count": len(rows),
        "edge_count": len(edges),
        "collision_count": len(collisions),
        "type_counts": dict(type_counts),
        "state_counts": {"confirmed": counts.get("confirmed", 0), "candidate": counts.get("candidate", 0), "rejected": counts.get("rejected", 0), "uncertain": counts.get("uncertain", 0), "needs_more_evidence": counts.get("needs_more_evidence", 0)},
        "aliases": rows,
        "edges": edges,
        "collision_sets": collisions,
        "dossier_rule": "One entity may have many aliases. One alias may appear across many unrelated entities. Confirm aliases with evidence and analyst state before creating identity assertions.",
    }


def export_entity_alias_graph_report(alias_graph: dict[str, Any], fmt: str = "json") -> tuple[str, str, str]:
    subject_id = alias_graph.get("subject_id") or "unknown"
    fmt = (fmt or "json").lower().strip()
    if fmt in {"md", "markdown"}:
        lines = [
            f"# Entity Alias Graph — Subject {subject_id}",
            "",
            f"Schema: `{SCHEMA}`",
            "",
            f"Aliases: {alias_graph.get('alias_count', 0)}",
            f"Edges: {alias_graph.get('edge_count', 0)}",
            f"Reverse-collision review sets: {alias_graph.get('collision_count', 0)}",
            "",
            "## Rule",
            "",
            alias_graph.get("dossier_rule", ""),
            "",
            "## Aliases",
            "",
        ]
        for alias in alias_graph.get("aliases", []):
            lines.extend([
                f"### {alias.get('alias_type')} — {alias.get('normalized_value')}",
                f"- State: {alias.get('analyst_state')}",
                f"- Confidence: {alias.get('confidence')}",
                f"- Evidence refs: {', '.join(alias.get('evidence_refs') or []) or 'n/a'}",
                f"- Candidate profiles: {', '.join(alias.get('candidate_ids') or []) or 'n/a'}",
                "",
            ])
        return "text/markdown", f"entity-alias-graph-subject-{subject_id}.md", "\n".join(lines)
    return "application/json", f"entity-alias-graph-subject-{subject_id}.json", json.dumps(alias_graph, indent=2, sort_keys=True)
