from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urlparse
from typing import Any

SCHEMA = "socmint.profile_fingerprint.v12_10_3"
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
    if first.lower() in {"user", "users", "profile", "profiles", "u", "@"} and "/" in path:
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


def candidate_key(observation: dict[str, Any]) -> tuple[str, str]:
    value = _norm(observation.get("value"))
    obs_type = observation.get("type")
    if obs_type in {"profile_url", "external_url"}:
        return (_domain(value), _username_from_url(value).lower() or value.lower())
    context = observation.get("payload", {}).get("context", {}) if isinstance(observation.get("payload"), dict) else {}
    platform = _lower(context.get("platform") or context.get("platform_hint") or observation.get("connector") or "unknown")
    return (platform, value.lower())


def _candidate_from_observation(observation: dict[str, Any], seeds: list[dict[str, Any]]) -> dict[str, Any] | None:
    obs_type = observation.get("type")
    if obs_type not in PROFILE_TYPES:
        return None
    value = _norm(observation.get("value"))
    if not value:
        return None
    payload = observation.get("payload") if isinstance(observation.get("payload"), dict) else {}
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    if obs_type in {"profile_url", "external_url"}:
        platform = _domain(value)
        username = _username_from_url(value)
        profile_url = value
    else:
        platform = _norm(context.get("platform") or context.get("platform_hint") or value)
        username = _norm(context.get("target") or next(iter(_seed_usernames(seeds)), ""))
        profile_url = _norm(context.get("url") or context.get("profile_url") or "")
    fingerprint = {
        "username": username,
        "platform": platform,
        "profile_url": profile_url,
        "display_name": _norm(context.get("display_name") or context.get("name")),
        "bio_text": _norm(context.get("bio") or context.get("description")),
        "location": _norm(context.get("location")),
        "linked_urls": sorted(set(context.get("linked_urls") or [])) if isinstance(context.get("linked_urls"), list) else [],
        "avatar_url": _norm(context.get("avatar_url") or context.get("image")),
        "source_connectors": sorted({_norm(observation.get("connector") or payload.get("source") or "unknown")}),
    }
    fingerprint["fingerprint_hash"] = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
    return {
        "candidate_id": fingerprint["fingerprint_hash"][:16],
        "subject_id": observation.get("subject_id"),
        "observation_ids": [observation.get("id")],
        "source_refs": [observation.get("source_ref")],
        "evidence_refs": [observation.get("evidence_ref")],
        "observation_types": [obs_type],
        "profile_fingerprint": fingerprint,
        "raw_values": [value],
    }


def merge_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for cand in candidates:
        fp = cand["profile_fingerprint"]
        key = (_lower(fp.get("platform")), _lower(fp.get("username") or fp.get("profile_url")))
        if key not in grouped:
            grouped[key] = cand
            continue
        target = grouped[key]
        target["observation_ids"].extend(x for x in cand["observation_ids"] if x not in target["observation_ids"])
        target["source_refs"].extend(x for x in cand["source_refs"] if x and x not in target["source_refs"])
        target["evidence_refs"].extend(x for x in cand["evidence_refs"] if x and x not in target["evidence_refs"])
        target["observation_types"] = sorted(set(target["observation_types"] + cand["observation_types"]))
        target["raw_values"] = sorted(set(target["raw_values"] + cand["raw_values"]))
        target["profile_fingerprint"]["source_connectors"] = sorted(set(target["profile_fingerprint"].get("source_connectors", []) + cand["profile_fingerprint"].get("source_connectors", [])))
        for field in ("profile_url", "display_name", "bio_text", "location", "avatar_url"):
            if not target["profile_fingerprint"].get(field) and cand["profile_fingerprint"].get(field):
                target["profile_fingerprint"][field] = cand["profile_fingerprint"][field]
    return list(grouped.values())


def score_candidate(candidate: dict[str, Any], seeds: list[dict[str, Any]], assertions: list[dict[str, Any]]) -> dict[str, Any]:
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
    linked = fp.get("linked_urls") or []
    if linked:
        score += 0.15
        positive.append("candidate has linked URLs available for cross-link analysis")
    if fp.get("avatar_url"):
        score += 0.10
        positive.append("candidate has reusable visual asset signal available")
    if fp.get("display_name"):
        score += 0.08
        positive.append("candidate has display-name text available")
    if fp.get("bio_text"):
        score += 0.06
        positive.append("candidate has bio text available")
    if candidate.get("observation_types") and set(candidate["observation_types"]).issubset(USERNAME_ONLY_TYPES):
        score -= 0.20
        negative.append("username/platform-only observation; no profile URL or cross-link proof")
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
    candidate.update({
        "schema": SCHEMA,
        "identity_score": score,
        "collision_status": status,
        "review_state": "unreviewed",
        "dossier_ready": score >= LIKELY_THRESHOLD,
        "positive_reasons": positive,
        "negative_reasons": negative,
        "dossier_rule": "Username-only candidates are excluded from dossier-ready assertions until corroborated and analyst-reviewed.",
    })
    return candidate


def build_profile_fingerprint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    seeds = payload.get("seeds", [])
    assertions = payload.get("assertions", [])
    raw_candidates = []
    for obs in payload.get("observations", []):
        cand = _candidate_from_observation(obs, seeds)
        if cand:
            raw_candidates.append(cand)
    candidates = [score_candidate(cand, seeds, assertions) for cand in merge_candidates(raw_candidates)]
    candidates.sort(key=lambda item: item.get("identity_score", 0), reverse=True)
    counts = {
        "likely_same_online_identity": len([c for c in candidates if c["collision_status"] == "likely_same_online_identity"]),
        "possible_same_operator": len([c for c in candidates if c["collision_status"] == "possible_same_operator"]),
        "weak_username_collision": len([c for c in candidates if c["collision_status"] == "weak_username_collision"]),
        "likely_username_collision": len([c for c in candidates if c["collision_status"] == "likely_username_collision"]),
    }
    return {
        "schema": SCHEMA,
        "subject_id": payload.get("subject", {}).get("id"),
        "candidate_count": len(candidates),
        "needs_review_count": len([c for c in candidates if not c.get("dossier_ready")]),
        "dossier_ready_count": len([c for c in candidates if c.get("dossier_ready")]),
        "collision_counts": counts,
        "candidates": candidates,
        "gate": {
            "status": "review" if candidates else "empty",
            "rule": "No username-only or weak-collision candidate can enter dossier-ready assertions without corroboration and analyst review.",
        },
    }
