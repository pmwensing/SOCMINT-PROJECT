import json
import logging
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import database as db
from .config import load_settings
from .media_profile import enrich_url_observation
from .url_security import (
    MAX_REDIRECTS,
    normalize_and_validate_url,
    validated_redirect_url,
)

logger = logging.getLogger(__name__)

session = requests.Session()
retry = Retry(total=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)
session.headers.update({"User-Agent": "SOCMINT-Profile-Enricher/1.0"})

URL_RE = re.compile(r"https?://[\w\-.$%&?=/#+:]+")
IMAGE_EXT_RE = re.compile(
    r'https?://[^\s"]+\.(?:jpg|jpeg|png|gif|webp)', re.IGNORECASE
)
ENRICHMENT_PROMOTION_THRESHOLD = 0.55
SENSITIVE_EXPANSION_TYPES = {
    "email",
    "phone",
    "profile_email",
    "profile_phone",
}
CONTEXT_LINK_KEYS = {
    "name",
    "display_name",
    "location",
    "address",
    "city",
    "region",
    "country",
}


def _json_loads(value, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(value or "{}")
    except json.JSONDecodeError:
        return default


def load_json_if_possible(text):
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("{") or cleaned.startswith("["):
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None
    return None


def extract_urls(text):
    if not text:
        return []
    return list(set(URL_RE.findall(text)))


def extract_media_urls(text):
    if not text:
        return []
    return list(set(IMAGE_EXT_RE.findall(text)))


def scrape_profile_url(url):
    time.sleep(1)
    settings = load_settings(require_secret=False)
    url = normalize_and_validate_url(url, allow_onion=bool(settings.tor_proxy))
    if not url:
        logger.warning("Skipped unsafe profile URL")
        return None

    request_kwargs = {"timeout": 15, "allow_redirects": False}
    if settings.tor_proxy:
        request_kwargs["proxies"] = {
            "http": settings.tor_proxy,
            "https": settings.tor_proxy,
        }

    try:
        response = None
        for _ in range(MAX_REDIRECTS + 1):
            response = session.get(url, **request_kwargs)
            if not response.is_redirect:
                break
            next_url = validated_redirect_url(
                url,
                response.headers.get("Location"),
                allow_onion=bool(settings.tor_proxy),
            )
            response.close()
            if not next_url:
                logger.warning("Skipped unsafe profile redirect")
                return None
            url = next_url
        if response is not None and response.is_redirect:
            response.close()
            return None
        response.raise_for_status()
        logger.info("Scraped profile URL: %s", url)
    except Exception as exc:
        logger.error("Failed to scrape %s: %s", url, exc)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    result = {
        "url": url,
        "title": None,
        "description": None,
        "site_name": None,
        "image": None,
        "raw_html": None,
    }

    title = soup.find("title")
    if title:
        result["title"] = title.get_text(strip=True)

    def meta(name):
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag.get("content").strip()
        tag = soup.find("meta", attrs={"property": name})
        if tag and tag.get("content"):
            return tag.get("content").strip()
        return None

    result["description"] = meta("description") or meta("og:description")
    result["site_name"] = meta("og:site_name")
    result["image"] = meta("og:image") or meta("twitter:image")
    result["raw_html"] = response.text[:10000]
    return result


def parse_tool_output(tool_name, raw_output):
    parsed = {
        "tool": tool_name,
        "raw": raw_output,
        "urls": [],
        "media_urls": [],
        "json": None,
    }
    if isinstance(raw_output, str):
        parsed["urls"] = extract_urls(raw_output)
        parsed["media_urls"] = extract_media_urls(raw_output)
        parsed_json = load_json_if_possible(raw_output)
        if parsed_json is not None:
            parsed["json"] = parsed_json
            if isinstance(parsed_json, dict):
                json_text = json.dumps(parsed_json)
                parsed["urls"] = list(set(parsed["urls"] + extract_urls(json_text)))
                parsed["media_urls"] = list(
                    set(parsed["media_urls"] + extract_media_urls(json_text))
                )
    else:
        try:
            parsed["json"] = raw_output
            parsed["urls"] = extract_urls(json.dumps(raw_output))
        except Exception:
            pass
    return parsed


def _host(value):
    parsed = urlparse(value or "")
    return (parsed.hostname or "").lower().removeprefix("www.")


def _domain_match(left, right):
    left_host = _host(left)
    right_host = _host(right)
    if not left_host or not right_host:
        return False
    return (
        left_host == right_host
        or left_host.endswith(f".{right_host}")
        or right_host.endswith(f".{left_host}")
    )


def _normalized_text(value):
    return str(value or "").strip().lower()


def _compact_text(value):
    return re.sub(r"[^a-z0-9]+", "", _normalized_text(value))


def _context_values(finding):
    context = finding.get("context") if isinstance(finding, dict) else None
    if not isinstance(context, dict):
        return []

    values = []
    for key, value in context.items():
        if str(key).lower() not in CONTEXT_LINK_KEYS:
            continue
        if isinstance(value, (str, int, float)):
            values.append(_normalized_text(value))
    return [value for value in values if value]


def _has_contextual_seed_link(finding, parent_observation, seeds):
    context_values = _context_values(finding)
    if not context_values:
        return False, []

    parent_value = _normalized_text(parent_observation.normalized_value)
    reasons = []
    for seed in seeds:
        seed_value = _normalized_text(seed.normalized_value)
        compact_seed = _compact_text(seed.normalized_value)
        if not seed_value:
            continue
        compact_context_values = [_compact_text(value) for value in context_values]
        if any(seed_value in value or value in seed_value for value in context_values):
            reasons.append(f"context_links_to_{seed.seed_type}_seed")
        elif compact_seed and any(
            compact_seed in value or value in compact_seed
            for value in compact_context_values
        ):
            reasons.append(f"context_name_links_to_{seed.seed_type}_seed")
        if any(value and value in parent_value for value in context_values):
            reasons.append("context_links_to_parent_observation")

    return bool(reasons), sorted(set(reasons))


def score_enrichment_correlation(finding, parent_observation, seeds) -> dict:
    """Score whether an enrichment finding still belongs to the subject seed."""
    value = str(finding.get("value") or "").strip()
    finding_type = str(finding.get("type") or "")
    parent_value = parent_observation.normalized_value or ""
    parent_confidence = float(parent_observation.confidence or 0.0)
    score = 0.0
    reasons = []

    if value and value == parent_value:
        score += 0.35
        reasons.append("finding_value_matches_parent_observation")

    if _domain_match(value, parent_value):
        score += 0.3
        reasons.append("finding_domain_matches_parent_observation")

    if finding_type == "profile_platform" and _host(parent_value):
        platform = _normalized_text(value)
        if platform and platform in _host(parent_value):
            score += 0.3
            reasons.append("platform_matches_parent_observation_host")

    for seed in seeds:
        seed_value = _normalized_text(seed.normalized_value)
        finding_value = _normalized_text(value)
        parent_text = _normalized_text(parent_value)
        if not seed_value:
            continue

        if seed.seed_type in {"username", "email", "phone"}:
            if finding_value == seed_value:
                score += 0.45
                reasons.append(f"finding_matches_{seed.seed_type}_seed")
            elif seed_value in finding_value:
                score += 0.3
                reasons.append(f"finding_contains_{seed.seed_type}_seed")
            if seed_value in parent_text:
                score += 0.25
                reasons.append(f"parent_observation_contains_{seed.seed_type}_seed")

        if seed.seed_type == "url":
            if value == seed.normalized_value:
                score += 0.45
                reasons.append("finding_matches_url_seed")
            if parent_value == seed.normalized_value:
                score += 0.3
                reasons.append("parent_observation_matches_url_seed")
            if _domain_match(value, seed.normalized_value):
                score += 0.25
                reasons.append("finding_domain_matches_url_seed")
            if _domain_match(parent_value, seed.normalized_value):
                score += 0.25
                reasons.append("parent_domain_matches_url_seed")

    if parent_confidence:
        score += min(0.2, parent_confidence * 0.2)
        reasons.append("parent_observation_confidence_contributes")

    score = round(min(score, 1.0), 3)
    state = (
        "promoted"
        if score >= ENRICHMENT_PROMOTION_THRESHOLD
        else "quarantined"
    )
    review_reasons = []
    if finding_type in SENSITIVE_EXPANSION_TYPES and state == "quarantined":
        has_context_link, review_reasons = _has_contextual_seed_link(
            finding,
            parent_observation,
            seeds,
        )
        if has_context_link:
            state = "needs_human_review"
            reasons.extend(review_reasons)

    return {
        "score": score,
        "threshold": ENRICHMENT_PROMOTION_THRESHOLD,
        "state": state,
        "reasons": sorted(set(reasons)),
        "review_reasons": review_reasons,
        "parent_observation_id": parent_observation.id,
        "parent_observation_value": parent_value,
        "seed_ids": [seed.id for seed in seeds],
        "expansion_depth": 2,
        "requires_human_review": state == "needs_human_review",
    }


def enrich_subject_media_profiles(subject_id: int) -> dict:
    if not db.get_spine_subject(subject_id):
        raise ValueError("Subject not found.")

    seeds = db.list_spine_seeds(subject_id)
    created = []
    promoted = 0
    quarantined = 0
    review_required = 0
    for obs in db.list_spine_observations(subject_id):
        value = obs.normalized_value or ""
        if not value.startswith(("http://", "https://")):
            continue

        result = enrich_url_observation(value)
        artifact = result.get("artifact") or {}
        enrichment_type = result.get("adapter", "profile_media_enrichment")
        correlated_findings = []
        for finding in result.get("findings", []):
            annotated = dict(finding)
            annotated["correlation"] = score_enrichment_correlation(
                finding,
                obs,
                seeds,
            )
            correlated_findings.append(annotated)

        result["findings"] = correlated_findings
        result["correlation_policy"] = {
            "threshold": ENRICHMENT_PROMOTION_THRESHOLD,
            "promotion_rule": (
                "Only findings correlated to subject seeds or parent observations "
                "are promoted into spine observations."
            ),
        }
        enrichment_id = db.create_media_profile_enrichment(
            subject_id=subject_id,
            observation_id=obs.id,
            enrichment_type=enrichment_type,
            status=result.get("status", "unknown"),
            source_value=value,
            artifact_ref=artifact.get("sha256"),
            payload=result,
        )
        created.append(enrichment_id)

        for finding in correlated_findings:
            correlation = finding.get("correlation") or {}
            if correlation.get("state") != "promoted":
                if correlation.get("state") == "needs_human_review":
                    review_required += 1
                quarantined += 1
                continue
            promoted += 1
            db.create_spine_observation(
                subject_id=subject_id,
                run_id=obs.run_id,
                observation_type=finding.get("type", "enrichment_finding"),
                normalized_value=str(finding.get("value", "")),
                confidence=str(finding.get("confidence", 0.5)),
                source_ref=f"enrichment:{enrichment_id}:{enrichment_type}",
                evidence_ref=f"sha256:{artifact.get('sha256')}"
                if artifact.get("sha256")
                else obs.evidence_ref,
                payload=finding,
            )

    assertion_ids = []
    if promoted:
        from .spine import correlate_subject

        assertion_ids = correlate_subject(subject_id)

    return {
        "subject_id": subject_id,
        "enrichment_ids": created,
        "promoted_findings": promoted,
        "quarantined_findings": quarantined,
        "review_required_findings": review_required,
        "assertion_ids": assertion_ids,
    }


def media_profile_payload(subject_id: int) -> dict:
    enrichments = db.list_media_profile_enrichments(subject_id)
    return {
        "subject_id": subject_id,
        "enrichments": [
            {
                "id": item.id,
                "observation_id": item.observation_id,
                "type": item.enrichment_type,
                "status": item.status,
                "source_value": item.source_value,
                "artifact_ref": item.artifact_ref,
                "payload": _json_loads(item.payload_json),
                "created_at": item.created_at.isoformat()
                if item.created_at
                else None,
            }
            for item in enrichments
        ],
    }



def enrich_dossier(dossier):
    """Backward-compatible enrichment hook for legacy CLI generation.

    The v6+ production spine uses subject-level enrichment via
    enrich_subject_media_profiles().  The older CLI path still imports and
    calls enrich_dossier(), so keep this lightweight compatibility wrapper to
    prevent dashboard startup/import failures.
    """
    if not isinstance(dossier, dict):
        return dossier

    enriched = dict(dossier)
    enriched.setdefault("enrichment", {})
    enriched["enrichment"].setdefault("status", "legacy_compat")
    enriched["enrichment"].setdefault(
        "note",
        "Use the v6+ dossier spine/workbench for production enrichment.",
    )
    return enriched
