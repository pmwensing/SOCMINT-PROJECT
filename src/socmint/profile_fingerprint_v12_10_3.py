from __future__ import annotations

import hashlib
import json
from urllib.parse import urlparse
from typing import Any

SCHEMA = "socmint.profile_fingerprint.v12_10_3"
PIPELINE = [
    "connector_finding",
    "candidate_profile",
    "profile_fingerprint",
    "collision_resolver",
    "identity_link_hypothesis",
    "analyst_review",
    "dossier_assertion",
]
PROFILE_TYPES = {"profile_url", "external_url", "account_presence", "platform_presence"}
USERNAME_ONLY_TYPES = {"account_presence", "platform_presence"}
LIKELY_THRESHOLD = 0.80
POSSIBLE_THRESHOLD = 0.60
WEAK_THRESHOLD = 0.35


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _norm(value).lower()


def _domain(url: str) -> str:
    parsed = urlparse(_norm(url))
    return (parsed.netloc or parsed.path.split("/", 1)[0]).lower().removeprefix("www.")


def _username_from_url(url: str) -> str:
    parsed = urlparse(_norm(url))
    path = parsed.path.strip("/")
    if not path:
        return ""
    first = path.split("/", 1)[0]
    if (
        first.lower() in {"user", "users", "profile", "profiles", "u", "@"}
        and "/" in path
    ):
        return path.split("/", 2)[1]
    return first.lstrip("@")


def _seed_usernames(seeds: list[dict[str, Any]]) -> set[str]:
    values: set[str] = set()
    for seed in seeds:
        value = _lower(seed.get("value"))
        if not value:
            continue
        if seed.get("type") == "email" and "@" in value:
            values.add(value.split("@", 1)[0])
        if seed.get("type") == "username":
            values.add(value)
    return values


def _seed_domains(seeds: list[dict[str, Any]]) -> set[str]:
    domains: set[str] = set()
    for seed in seeds:
        value = _lower(seed.get("value"))
        if seed.get("type") == "url" and value:
            domains.add(_domain(value))
        if seed.get("type") == "email" and "@" in value:
            domains.add(value.split("@", 1)[1])
    return domains


def connector_finding_from_observation(
    observation: dict[str, Any],
) -> dict[str, Any] | None:
    if observation.get("type") not in PROFILE_TYPES:
        return None
    value = _norm(observation.get("value"))
    if not value:
        return None
    return {
        "stage": "connector_finding",
        "observation_id": observation.get("id"),
        "run_id": observation.get("run_id"),
        "source_ref": observation.get("source_ref"),
        "evidence_ref": observation.get("evidence_ref"),
        "connector": observation.get("connector")
        or _norm(observation.get("source_ref")).split(":")[-1],
        "finding_type": observation.get("type"),
        "value": value,
        "payload": observation.get("payload")
        if isinstance(observation.get("payload"), dict)
        else {},
    }


def candidate_profile_from_finding(
    finding: dict[str, Any], seeds: list[dict[str, Any]]
) -> dict[str, Any]:
    value = _norm(finding.get("value"))
    obs_type = finding.get("finding_type")
    payload = finding.get("payload") if isinstance(finding.get("payload"), dict) else {}
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    if obs_type in {"profile_url", "external_url"}:
        platform = _domain(value)
        username = _username_from_url(value)
        profile_url = value
    else:
        platform = _norm(
            context.get("platform") or context.get("platform_hint") or value
        )
        username = _norm(
            context.get("target") or next(iter(_seed_usernames(seeds)), "")
        )
        profile_url = _norm(context.get("url") or context.get("profile_url") or "")
    candidate_core = {
        "platform": platform,
        "username": username,
        "profile_url": profile_url,
        "raw_value": value,
        "finding_type": obs_type,
        "source_connector": finding.get("connector"),
    }
    candidate_id = hashlib.sha256(
        json.dumps(candidate_core, sort_keys=True).encode()
    ).hexdigest()[:16]
    return {
        "stage": "candidate_profile",
        "candidate_id": candidate_id,
        "subject_id": finding.get("subject_id"),
        "platform": platform,
        "username": username,
        "profile_url": profile_url,
        "raw_value": value,
        "source_connector": finding.get("connector"),
        "observation_ids": [finding.get("observation_id")],
        "source_refs": [finding.get("source_ref")],
        "evidence_refs": [finding.get("evidence_ref")],
        "finding_types": [obs_type],
        "context": context,
    }


def profile_fingerprint_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    context = (
        candidate.get("context") if isinstance(candidate.get("context"), dict) else {}
    )
    fingerprint = {
        "stage": "profile_fingerprint",
        "username": _norm(candidate.get("username")),
        "platform": _norm(candidate.get("platform")),
        "profile_url": _norm(candidate.get("profile_url")),
        "display_name": _norm(context.get("display_name") or context.get("name")),
        "bio_text": _norm(context.get("bio") or context.get("description")),
        "location": _norm(context.get("location")),
        "linked_urls": sorted(set(context.get("linked_urls") or []))
        if isinstance(context.get("linked_urls"), list)
        else [],
        "avatar_url": _norm(context.get("avatar_url") or context.get("image")),
        "avatar_phash": _norm(context.get("avatar_phash")),
        "banner_phash": _norm(context.get("banner_phash")),
        "source_connectors": sorted(
            {_norm(candidate.get("source_connector") or "unknown")}
        ),
    }
    fingerprint["fingerprint_hash"] = hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True).encode()
    ).hexdigest()
    return fingerprint


def merge_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for cand in candidates:
        fp = cand["profile_fingerprint"]
        key = (
            _lower(fp.get("platform")),
            _lower(fp.get("username") or fp.get("profile_url")),
        )
        if key not in grouped:
            grouped[key] = cand
            continue
        target = grouped[key]
        target["observation_ids"].extend(
            x for x in cand["observation_ids"] if x not in target["observation_ids"]
        )
        target["source_refs"].extend(
            x for x in cand["source_refs"] if x and x not in target["source_refs"]
        )
        target["evidence_refs"].extend(
            x for x in cand["evidence_refs"] if x and x not in target["evidence_refs"]
        )
        target["finding_types"] = sorted(
            set(target["finding_types"] + cand["finding_types"])
        )
        target["raw_values"] = sorted(
            set(target.get("raw_values", []) + cand.get("raw_values", []))
        )
        target["profile_fingerprint"]["source_connectors"] = sorted(
            set(
                target["profile_fingerprint"].get("source_connectors", [])
                + cand["profile_fingerprint"].get("source_connectors", [])
            )
        )
        for field in (
            "profile_url",
            "display_name",
            "bio_text",
            "location",
            "avatar_url",
            "avatar_phash",
            "banner_phash",
        ):
            if not target["profile_fingerprint"].get(field) and cand[
                "profile_fingerprint"
            ].get(field):
                target["profile_fingerprint"][field] = cand["profile_fingerprint"][
                    field
                ]
    return list(grouped.values())


def collision_resolver(
    candidate: dict[str, Any], seeds: list[dict[str, Any]]
) -> dict[str, Any]:
    fp = candidate["profile_fingerprint"]
    seed_names = _seed_usernames(seeds)
    seed_domains = _seed_domains(seeds)
    score = 0.0
    positive: list[str] = []
    negative: list[str] = []
    username = _lower(fp.get("username"))
    profile_url = _lower(fp.get("profile_url"))
    platform = _lower(fp.get("platform"))
    if username and username in seed_names:
        score += 0.25
        positive.append("username matches a known subject seed or email local-part")
    elif any(name and name in profile_url for name in seed_names):
        score += 0.18
        positive.append("profile URL contains a known subject username seed")
    else:
        negative.append("no non-URL identity signal beyond connector/platform presence")
    if profile_url:
        score += 0.12
        positive.append("profile URL was observed, not just a platform label")
    if len(fp.get("source_connectors") or []) >= 2:
        score += 0.10
        positive.append("candidate is corroborated by two or more connectors")
    if any(domain and domain in profile_url for domain in seed_domains):
        score += 0.18
        positive.append("profile URL or linked URL overlaps a known seed domain")
    if fp.get("linked_urls"):
        score += 0.15
        positive.append("candidate has linked URLs available for cross-link analysis")
    if fp.get("avatar_phash") or fp.get("avatar_url"):
        score += 0.10
        positive.append("candidate has reusable visual asset signal available")
    if fp.get("display_name"):
        score += 0.08
        positive.append("candidate has display-name text available")
    if fp.get("bio_text"):
        score += 0.06
        positive.append("candidate has bio text available")
    if set(candidate.get("finding_types") or []).issubset(USERNAME_ONLY_TYPES):
        score -= 0.20
        negative.append(
            "username/platform-only observation; no profile URL or cross-link proof"
        )
    if platform in {"unknown", ""}:
        score -= 0.08
        negative.append("platform could not be resolved")
    score = max(0.0, min(1.0, round(score, 3)))
    if score >= LIKELY_THRESHOLD:
        status = "likely_same_online_identity"
    elif score >= POSSIBLE_THRESHOLD:
        status = "possible_same_operator"
    elif score >= WEAK_THRESHOLD:
        status = "weak_username_collision"
    else:
        status = "likely_username_collision"
    return {
        "stage": "collision_resolver",
        "identity_score": score,
        "collision_status": status,
        "positive_reasons": positive,
        "negative_reasons": negative,
    }


def identity_link_hypothesis(candidate: dict[str, Any]) -> dict[str, Any]:
    resolver = candidate["collision_resolution"]
    status = resolver["collision_status"]
    relationship = {
        "likely_same_online_identity": "candidate_profile_likely_same_online_identity_cluster",
        "possible_same_operator": "candidate_profile_possible_same_operator",
        "weak_username_collision": "candidate_profile_weak_username_collision",
        "likely_username_collision": "candidate_profile_likely_unrelated_username_collision",
    }[status]
    can_promote = status == "likely_same_online_identity"
    return {
        "stage": "identity_link_hypothesis",
        "relationship": relationship,
        "confidence": resolver["identity_score"],
        "can_promote_to_dossier_assertion": can_promote,
        "dossier_language": "Likely same online identity cluster"
        if can_promote
        else "Unconfirmed candidate account; do not treat as same entity without analyst review and corroboration.",
    }


def analyst_review_state(candidate: dict[str, Any]) -> dict[str, Any]:
    hypothesis = candidate["identity_link_hypothesis"]
    return {
        "stage": "analyst_review",
        "review_state": "unreviewed",
        "available_actions": [
            "accept_same_entity",
            "reject_collision",
            "mark_uncertain",
            "request_more_evidence",
        ],
        "recommended_action": "accept_same_entity"
        if hypothesis["can_promote_to_dossier_assertion"]
        else "request_more_evidence",
    }


def dossier_assertion_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    hypothesis = candidate["identity_link_hypothesis"]
    review = candidate["analyst_review"]
    ready = (
        hypothesis["can_promote_to_dossier_assertion"]
        and review["review_state"] == "accepted"
    )
    return {
        "stage": "dossier_assertion",
        "dossier_ready": ready,
        "blocked_reason": None
        if ready
        else "Candidate remains a hypothesis until analyst acceptance; username-only/weak collision findings are excluded.",
        "assertion_type": "same_online_identity_cluster"
        if ready
        else "candidate_profile_hypothesis",
    }


def build_profile_fingerprint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    seeds = payload.get("seeds", [])
    findings = []
    raw_candidates = []
    for obs in payload.get("observations", []):
        finding = connector_finding_from_observation(obs)
        if not finding:
            continue
        finding["subject_id"] = obs.get("subject_id")
        findings.append(finding)
        candidate = candidate_profile_from_finding(finding, seeds)
        candidate["raw_values"] = [finding["value"]]
        candidate["profile_fingerprint"] = profile_fingerprint_from_candidate(candidate)
        raw_candidates.append(candidate)
    candidates = merge_candidates(raw_candidates)
    for candidate in candidates:
        candidate["collision_resolution"] = collision_resolver(candidate, seeds)
        candidate["identity_score"] = candidate["collision_resolution"][
            "identity_score"
        ]
        candidate["collision_status"] = candidate["collision_resolution"][
            "collision_status"
        ]
        candidate["positive_reasons"] = candidate["collision_resolution"][
            "positive_reasons"
        ]
        candidate["negative_reasons"] = candidate["collision_resolution"][
            "negative_reasons"
        ]
        candidate["identity_link_hypothesis"] = identity_link_hypothesis(candidate)
        candidate["analyst_review"] = analyst_review_state(candidate)
        candidate["dossier_assertion_gate"] = dossier_assertion_gate(candidate)
        candidate["dossier_ready"] = candidate["dossier_assertion_gate"][
            "dossier_ready"
        ]
        candidate["pipeline_trace"] = PIPELINE
        candidate["dossier_rule"] = (
            "No username-only or weak-collision candidate can enter dossier-ready assertions without corroboration and analyst review."
        )
    candidates.sort(key=lambda item: item.get("identity_score", 0), reverse=True)
    counts = {
        "likely_same_online_identity": len(
            [
                c
                for c in candidates
                if c["collision_status"] == "likely_same_online_identity"
            ]
        ),
        "possible_same_operator": len(
            [c for c in candidates if c["collision_status"] == "possible_same_operator"]
        ),
        "weak_username_collision": len(
            [
                c
                for c in candidates
                if c["collision_status"] == "weak_username_collision"
            ]
        ),
        "likely_username_collision": len(
            [
                c
                for c in candidates
                if c["collision_status"] == "likely_username_collision"
            ]
        ),
    }
    return {
        "schema": SCHEMA,
        "pipeline": PIPELINE,
        "subject_id": payload.get("subject", {}).get("id"),
        "connector_finding_count": len(findings),
        "candidate_count": len(candidates),
        "needs_review_count": len(
            [c for c in candidates if not c.get("dossier_ready")]
        ),
        "dossier_ready_count": len([c for c in candidates if c.get("dossier_ready")]),
        "collision_counts": counts,
        "connector_findings": findings,
        "candidates": candidates,
        "gate": {
            "status": "review" if candidates else "empty",
            "rule": "Connector Finding → Candidate Profile → Profile Fingerprint → Collision Resolver → Identity Link Hypothesis → Analyst Review → Dossier Assertion. No username-only candidate bypasses review.",
        },
    }
