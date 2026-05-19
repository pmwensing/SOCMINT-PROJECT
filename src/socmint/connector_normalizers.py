from __future__ import annotations

import json
import re
from typing import Any

NORMALIZER_SCHEMA = "socmint.connector_normalizers.v12_10_2"

PROFILE_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
PLATFORM_LINE_RE = re.compile(r"(?im)^\s*([A-Za-z0-9_. -]{2,60})\s*[:=]\s*(found|exists|registered|used|true|yes|valid|invalid|not found|false|no)\s*$")
PHONE_META_RE = re.compile(r"(?im)^\s*(country|carrier|line type|number type|valid|possible|region|timezone)\s*[:=]\s*(.+)$")
BREACH_RE = re.compile(r"(?i)(breach|leak|compromised|paste|pwned|exposure|database|found).*?([A-Za-z0-9_. -]{3,120})")


def _parse_json_maybe(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _text_from_result(raw_result: dict[str, Any]) -> str:
    chunks = []
    for key in ("stdout", "stderr", "message", "reason"):
        value = raw_result.get(key)
        if value:
            chunks.append(str(value))
    if raw_result.get("snapshots"):
        chunks.append(json.dumps(raw_result.get("snapshots"), sort_keys=True))
    if raw_result.get("findings"):
        chunks.append(json.dumps(raw_result.get("findings"), sort_keys=True))
    return "\n".join(chunks)


def _add(findings: list[dict[str, Any]], seen: set[tuple[str, str]], kind: str, value: str, source: str, confidence: float, context: dict[str, Any] | None = None) -> None:
    value = str(value or "").strip().rstrip(".,;)")
    if not value:
        return
    key = (kind, value.lower())
    if key in seen:
        return
    seen.add(key)
    findings.append({"type": kind, "value": value, "source": source, "confidence": round(float(confidence), 3), "context": context or {}})


def _add_structured_findings(findings: list[dict[str, Any]], seen: set[tuple[str, str]], raw_result: dict[str, Any], connector: str) -> None:
    for finding in raw_result.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        kind = str(finding.get("type") or "connector_finding").strip()
        value = finding.get("value") or finding.get("url")
        confidence = finding.get("confidence", 0.65)
        context = finding.get("context") or {}
        _add(findings, seen, kind, value, finding.get("source") or connector, confidence, context)


def normalize_connector_output(connector: str, seed_value: str, seed_type: str, raw_result: dict[str, Any]) -> list[dict[str, Any]]:
    connector = (connector or "unknown").strip().lower()
    normalizer = {
        "sherlock": normalize_sherlock,
        "maigret": normalize_maigret,
        "socialscan": normalize_socialscan,
        "social-analyzer": normalize_social_analyzer,
        "holehe": normalize_holehe,
        "h8mail": normalize_h8mail,
        "phoneinfoga": normalize_phoneinfoga,
        "archivebox": normalize_archivebox,
    }.get(connector, normalize_generic)
    return normalizer(seed_value, seed_type, raw_result, connector)


def normalize_generic(seed_value: str, seed_type: str, raw_result: dict[str, Any], connector: str = "generic") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    _add_structured_findings(findings, seen, raw_result, connector)
    text = _text_from_result(raw_result)
    for url in PROFILE_URL_RE.findall(text):
        _add(findings, seen, "external_url", url, connector, 0.62)
    for email in EMAIL_RE.findall(text):
        if email.lower() != str(seed_value).lower():
            _add(findings, seen, "email", email, connector, 0.58)
    for phone in PHONE_RE.findall(text):
        if re.sub(r"\D", "", phone) != re.sub(r"\D", "", str(seed_value)):
            _add(findings, seen, "phone", phone, connector, 0.56)
    return findings


def normalize_sherlock(seed_value: str, seed_type: str, raw_result: dict[str, Any], connector: str = "sherlock") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    _add_structured_findings(findings, seen, raw_result, connector)
    text = _text_from_result(raw_result)
    for url in PROFILE_URL_RE.findall(text):
        if "example.com" in url and raw_result.get("status") == "dry_run":
            continue
        _add(findings, seen, "profile_url", url, connector, 0.78, {"platform_hint": _platform_from_url(url)})
    for platform, state in PLATFORM_LINE_RE.findall(text):
        if state.lower() in {"found", "exists", "registered", "used", "true", "yes", "valid"}:
            _add(findings, seen, "platform_presence", platform.strip(), connector, 0.66, {"state": state})
    return findings


def normalize_maigret(seed_value: str, seed_type: str, raw_result: dict[str, Any], connector: str = "maigret") -> list[dict[str, Any]]:
    findings = normalize_sherlock(seed_value, seed_type, raw_result, connector)
    data = _parse_json_maybe(raw_result.get("stdout"))
    seen = {(item["type"], item["value"].lower()) for item in findings}
    if isinstance(data, dict):
        for site, item in data.items():
            if isinstance(item, dict):
                url = item.get("url") or item.get("profile_url") or item.get("url_main")
                status = str(item.get("status") or item.get("exists") or "").lower()
                if url and status not in {"not found", "false", "unknown"}:
                    _add(findings, seen, "profile_url", url, connector, 0.76, {"platform": site, "status": status})
    return findings


def normalize_socialscan(seed_value: str, seed_type: str, raw_result: dict[str, Any], connector: str = "socialscan") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    _add_structured_findings(findings, seen, raw_result, connector)
    text = _text_from_result(raw_result)
    for platform, state in PLATFORM_LINE_RE.findall(text):
        if state.lower() in {"found", "exists", "registered", "used", "true", "yes", "valid"}:
            _add(findings, seen, "account_presence", platform.strip(), connector, 0.68, {"target": seed_value, "state": state})
    data = _parse_json_maybe(raw_result.get("stdout"))
    _walk_presence_json(data, findings, seen, connector, seed_value)
    return findings


def normalize_social_analyzer(seed_value: str, seed_type: str, raw_result: dict[str, Any], connector: str = "social-analyzer") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    _add_structured_findings(findings, seen, raw_result, connector)
    data = _parse_json_maybe(raw_result.get("stdout"))
    _walk_social_analyzer_json(data, findings, seen, connector, seed_value)
    text = _text_from_result(raw_result)
    for url in PROFILE_URL_RE.findall(text):
        if "localhost" in url or "127.0.0.1" in url:
            continue
        _add(findings, seen, "profile_url", url, connector, 0.78, {"platform_hint": _platform_from_url(url), "deep_enrichment": True})
    return findings


def normalize_holehe(seed_value: str, seed_type: str, raw_result: dict[str, Any], connector: str = "holehe") -> list[dict[str, Any]]:
    findings = normalize_socialscan(seed_value, seed_type, raw_result, connector)
    seen = {(item["type"], item["value"].lower()) for item in findings}
    text = _text_from_result(raw_result)
    for line in text.splitlines():
        lowered = line.lower()
        if any(token in lowered for token in ("[+]", "used", "registered", "exists")):
            service = re.sub(r"[^A-Za-z0-9_. -]", " ", line).strip()
            service = re.sub(r"\s+", " ", service)[:80]
            if service:
                _add(findings, seen, "account_presence", service, connector, 0.67, {"target": seed_value})
    return findings


def normalize_h8mail(seed_value: str, seed_type: str, raw_result: dict[str, Any], connector: str = "h8mail") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    _add_structured_findings(findings, seen, raw_result, connector)
    text = _text_from_result(raw_result)
    for match in BREACH_RE.findall(text):
        label = match[1].strip() if isinstance(match, tuple) else str(match).strip()
        _add(findings, seen, "exposure_indicator", label, connector, 0.72, {"target": seed_value})
    for email in EMAIL_RE.findall(text):
        _add(findings, seen, "exposure_email_reference", email, connector, 0.62, {"target": seed_value})
    data = _parse_json_maybe(raw_result.get("stdout"))
    _walk_breach_json(data, findings, seen, connector, seed_value)
    return findings


def normalize_phoneinfoga(seed_value: str, seed_type: str, raw_result: dict[str, Any], connector: str = "phoneinfoga") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    _add_structured_findings(findings, seen, raw_result, connector)
    text = _text_from_result(raw_result)
    for label, value in PHONE_META_RE.findall(text):
        _add(findings, seen, f"phone_{label.lower().replace(' ', '_')}", value.strip(), connector, 0.7, {"target": seed_value})
    data = _parse_json_maybe(raw_result.get("stdout"))
    _walk_phone_json(data, findings, seen, connector, seed_value)
    return findings


def normalize_archivebox(seed_value: str, seed_type: str, raw_result: dict[str, Any], connector: str = "archivebox") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    status = str(raw_result.get("status") or "").lower()
    _add_structured_findings(findings, seen, raw_result, connector)
    if status == "dry_run":
        return findings
    for snapshot in raw_result.get("snapshots") or []:
        url = snapshot.get("url") or seed_value
        if snapshot.get("timestamp") or snapshot.get("index_path") or status == "completed":
            _add(findings, seen, "archive_snapshot", url, connector, 0.86, snapshot)
    for finding in raw_result.get("findings") or []:
        if finding.get("type") == "archive_candidate" and status != "completed":
            continue
        value = finding.get("value") or finding.get("url")
        if value:
            _add(findings, seen, finding.get("type", "archive_snapshot"), value, connector, finding.get("confidence", 0.78), finding.get("context") or {})
    return findings


def _platform_from_url(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", url, re.I)
    return match.group(1).lower() if match else "unknown"


def _walk_social_analyzer_json(data: Any, findings: list[dict[str, Any]], seen: set[tuple[str, str]], connector: str, target: str) -> None:
    if isinstance(data, dict):
        url = data.get("url") or data.get("link") or data.get("profile") or data.get("profile_url")
        site = data.get("site") or data.get("platform") or data.get("name") or data.get("website")
        status = str(data.get("status") or data.get("found") or data.get("exists") or data.get("valid") or "").lower()
        score = data.get("score") or data.get("rating") or data.get("confidence") or 78
        try:
            confidence = max(0.5, min(0.95, float(score) / 100 if float(score) > 1 else float(score)))
        except Exception:
            confidence = 0.78
        context = {"target": target, "platform": site, "status": status, "deep_enrichment": True}
        if url and status not in {"false", "not found", "missing", "unknown", "none"}:
            _add(findings, seen, "profile_url", str(url), connector, confidence, context)
        elif site and status in {"true", "found", "exists", "registered", "used", "valid", "yes"}:
            _add(findings, seen, "platform_presence", str(site), connector, confidence, context)
        for value in data.values():
            _walk_social_analyzer_json(value, findings, seen, connector, target)
    elif isinstance(data, list):
        for item in data:
            _walk_social_analyzer_json(item, findings, seen, connector, target)


def _walk_presence_json(data: Any, findings: list[dict[str, Any]], seen: set[tuple[str, str]], connector: str, target: str) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            lower = str(key).lower()
            if isinstance(value, bool) and value:
                _add(findings, seen, "account_presence", key, connector, 0.68, {"target": target})
            elif isinstance(value, str) and value.lower() in {"found", "exists", "registered", "used", "true", "valid"}:
                _add(findings, seen, "account_presence", key, connector, 0.68, {"target": target, "state": value})
            elif lower in {"site", "platform", "service"} and isinstance(value, str):
                _add(findings, seen, "account_presence", value, connector, 0.62, {"target": target})
            else:
                _walk_presence_json(value, findings, seen, connector, target)
    elif isinstance(data, list):
        for item in data:
            _walk_presence_json(item, findings, seen, connector, target)


def _walk_breach_json(data: Any, findings: list[dict[str, Any]], seen: set[tuple[str, str]], connector: str, target: str) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            lower = str(key).lower()
            if lower in {"breach", "breaches", "leak", "source", "database", "name"} and isinstance(value, str):
                _add(findings, seen, "exposure_indicator", value, connector, 0.72, {"target": target})
            else:
                _walk_breach_json(value, findings, seen, connector, target)
    elif isinstance(data, list):
        for item in data:
            _walk_breach_json(item, findings, seen, connector, target)


def _walk_phone_json(data: Any, findings: list[dict[str, Any]], seen: set[tuple[str, str]], connector: str, target: str) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            lower = str(key).lower().replace(" ", "_")
            if lower in {"country", "carrier", "line_type", "number_type", "valid", "possible", "region", "timezone"} and isinstance(value, (str, int, float, bool)):
                _add(findings, seen, f"phone_{lower}", str(value), connector, 0.7, {"target": target})
            else:
                _walk_phone_json(value, findings, seen, connector, target)
    elif isinstance(data, list):
        for item in data:
            _walk_phone_json(item, findings, seen, connector, target)
