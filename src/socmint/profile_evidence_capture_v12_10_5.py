from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .artifacts import artifact_root

SCHEMA = "socmint.profile_evidence_capture.v12_10_5"
CAPTURE_VERSION = "12.10.5"
ASSET_ONLY_DOMAINS = {
    "gravatar.com",
    "secure.gravatar.com",
    "avatars.githubusercontent.com",
    "github.githubassets.com",
    "static.xx.fbcdn.net",
    "pbs.twimg.com",
    "abs.twimg.com",
    "cdn.discordapp.com",
}
NON_PROFILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".css", ".js"}
PROFILE_PATH_HINTS = {"user", "users", "profile", "profiles", "u", "people", "person", "perfil", "accounts", "account", "add", "members", "member", "@"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _safe_slug(value: Any) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", _norm(value).lower()).strip("-.")
    return slug[:96] or "unknown"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_capture_file(base_dir: Path, filename: str, content: bytes) -> dict[str, Any]:
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / filename
    path.write_bytes(content)
    return {"path": str(path), "filename": filename, "sha256": _sha256_bytes(content), "size_bytes": len(content)}


def domain_for_url(url: str) -> str:
    parsed = urlparse(_norm(url))
    return (parsed.netloc or parsed.path.split("/", 1)[0]).lower().removeprefix("www.")


def enhanced_username_from_url(url: str) -> str:
    parsed = urlparse(_norm(url))
    path = parsed.path.strip("/")
    if not path:
        return ""
    parts = [part for part in path.split("/") if part]
    if not parts:
        return ""
    first = parts[0].lstrip("@")
    if parts[0].lower() in PROFILE_PATH_HINTS and len(parts) > 1:
        return parts[1].lstrip("@")
    return first


def is_asset_only_url(url: str) -> bool:
    value = _norm(url).lower()
    if not value:
        return False
    domain = domain_for_url(value)
    parsed = urlparse(value)
    path = parsed.path.lower()
    if any(domain == item or domain.endswith("." + item) for item in ASSET_ONLY_DOMAINS):
        if any(path.endswith(ext) for ext in NON_PROFILE_EXTENSIONS) or "/avatar" in path or "favicon" in path or "logo" in path:
            return True
    return any(path.endswith(ext) for ext in NON_PROFILE_EXTENSIONS)


def _extract_linked_urls(context: dict[str, Any], profile_url: str) -> list[str]:
    links: set[str] = set()
    for key in ("linked_urls", "links", "urls", "websites"):
        raw = context.get(key)
        if isinstance(raw, list):
            links.update(_norm(item) for item in raw if _norm(item))
        elif isinstance(raw, str) and raw.strip():
            links.add(raw.strip())
    for key in ("website", "url", "profile_url", "homepage"):
        raw = _norm(context.get(key))
        if raw and raw != profile_url:
            links.add(raw)
    return sorted(links)


def _stable_phash(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _capture_html(candidate: dict[str, Any], metadata: dict[str, Any]) -> str:
    fp = candidate.get("profile_fingerprint") or {}
    title = f"{fp.get('platform') or 'unknown'} / {fp.get('username') or 'unknown'}"
    return "\n".join([
        "<!doctype html>",
        "<html><head>",
        "<meta charset=\"utf-8\">",
        f"<title>{html.escape(title)}</title>",
        f"<meta name=\"socmint-schema\" content=\"{SCHEMA}\">",
        "</head><body>",
        f"<h1>{html.escape(title)}</h1>",
        f"<p>Profile URL: {html.escape(fp.get('profile_url') or '')}</p>",
        f"<p>Display name: {html.escape(fp.get('display_name') or '')}</p>",
        f"<p>Bio: {html.escape(fp.get('bio_text') or '')}</p>",
        f"<script type=\"application/json\" id=\"socmint-profile-capture\">{html.escape(json.dumps(metadata, sort_keys=True))}</script>",
        "</body></html>",
    ])


def _capture_screenshot_placeholder(metadata: dict[str, Any]) -> bytes:
    # Deterministic SVG placeholder. Live Playwright capture can replace this file later while keeping the same manifest schema.
    label = html.escape(str(metadata.get("profile_url") or metadata.get("candidate_id") or "candidate"))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" role="img" aria-label="SOCMINT profile capture placeholder">
  <rect width="1280" height="720" fill="#f8fafc"/>
  <rect x="48" y="48" width="1184" height="624" rx="24" fill="#ffffff" stroke="#0f172a" stroke-width="2"/>
  <text x="86" y="120" font-family="Arial" font-size="34" fill="#0f172a">SOCMINT Profile Evidence Capture</text>
  <text x="86" y="176" font-family="Arial" font-size="22" fill="#334155">{label}</text>
  <text x="86" y="236" font-family="Arial" font-size="18" fill="#475569">Deterministic evidence placeholder. Replace with live browser screenshot when capture is enabled.</text>
</svg>'''
    return svg.encode()


def capture_candidate_profile_artifacts(subject_id: int, candidate: dict[str, Any], live_capture_enabled: bool = False) -> dict[str, Any]:
    fp = candidate.get("profile_fingerprint") or {}
    profile_url = _norm(fp.get("profile_url"))
    candidate_id = _norm(candidate.get("candidate_id")) or _stable_phash(json.dumps(candidate, sort_keys=True))
    capture_id = hashlib.sha256(f"{subject_id}:{candidate_id}:{profile_url}".encode()).hexdigest()[:20]
    capture_dir = artifact_root() / "profile-evidence-captures" / f"subject-{int(subject_id)}" / _safe_slug(candidate_id)
    linked_urls = _extract_linked_urls(candidate.get("context") or {}, profile_url)
    metadata = {
        "schema": SCHEMA,
        "capture_version": CAPTURE_VERSION,
        "capture_id": capture_id,
        "subject_id": subject_id,
        "candidate_id": candidate_id,
        "captured_at": utc_now(),
        "live_capture_enabled": bool(live_capture_enabled),
        "profile_url": profile_url,
        "platform": _norm(fp.get("platform")),
        "username": _norm(fp.get("username")) or enhanced_username_from_url(profile_url),
        "display_name": _norm(fp.get("display_name")),
        "bio_text": _norm(fp.get("bio_text")),
        "location": _norm(fp.get("location")),
        "linked_urls": linked_urls,
        "avatar_url": _norm(fp.get("avatar_url")),
        "banner_url": _norm(fp.get("banner_url")),
        "asset_only_url": is_asset_only_url(profile_url),
        "non_profile_asset_signals": [],
    }
    for key in ("profile_url", "avatar_url", "banner_url"):
        if is_asset_only_url(metadata.get(key, "")):
            metadata["non_profile_asset_signals"].append(key)
    html_body = _capture_html(candidate, metadata).encode()
    html_file = _write_capture_file(capture_dir, "profile.html", html_body)
    screenshot_file = _write_capture_file(capture_dir, "screenshot.svg", _capture_screenshot_placeholder(metadata))
    metadata_file = _write_capture_file(capture_dir, "metadata.json", json.dumps(metadata, indent=2, sort_keys=True).encode())
    manifest = {
        "schema": SCHEMA,
        "capture_id": capture_id,
        "candidate_id": candidate_id,
        "subject_id": subject_id,
        "profile_url": profile_url,
        "captured_at": metadata["captured_at"],
        "mode": "live" if live_capture_enabled else "metadata_snapshot",
        "files": {"html": html_file, "screenshot": screenshot_file, "metadata": metadata_file},
        "chain_of_custody": [{"event": "profile_capture_created", "timestamp": metadata["captured_at"], "actor": "socmint-worker", "sha256": metadata_file["sha256"]}],
    }
    manifest_file = _write_capture_file(capture_dir, "capture-manifest.json", json.dumps(manifest, indent=2, sort_keys=True).encode())
    manifest["files"]["manifest"] = manifest_file
    return manifest


def enrich_candidate_profile_fingerprint(subject_id: int, candidate: dict[str, Any], live_capture_enabled: bool = False) -> dict[str, Any]:
    fp = candidate.setdefault("profile_fingerprint", {})
    profile_url = _norm(fp.get("profile_url"))
    context = candidate.get("context") if isinstance(candidate.get("context"), dict) else {}
    if profile_url and not fp.get("username"):
        fp["username"] = enhanced_username_from_url(profile_url)
    linked_urls = sorted(set((fp.get("linked_urls") or []) + _extract_linked_urls(context, profile_url)))
    fp["linked_urls"] = linked_urls
    if context.get("banner_url") and not fp.get("banner_url"):
        fp["banner_url"] = _norm(context.get("banner_url"))
    if fp.get("avatar_url") and not fp.get("avatar_phash"):
        fp["avatar_phash"] = _stable_phash(fp["avatar_url"])
    if fp.get("banner_url") and not fp.get("banner_phash"):
        fp["banner_phash"] = _stable_phash(fp["banner_url"])
    capture = capture_candidate_profile_artifacts(subject_id, candidate, live_capture_enabled=live_capture_enabled)
    fp["evidence_capture"] = capture
    fp["html_sha256"] = capture["files"]["html"]["sha256"]
    fp["screenshot_sha256"] = capture["files"]["screenshot"]["sha256"]
    fp["metadata_sha256"] = capture["files"]["metadata"]["sha256"]
    fp["asset_only_url"] = is_asset_only_url(profile_url)
    fp["text_fingerprint_hash"] = hashlib.sha256(json.dumps({"display_name": fp.get("display_name"), "bio_text": fp.get("bio_text"), "location": fp.get("location"), "linked_urls": linked_urls}, sort_keys=True).encode()).hexdigest()
    fp["visual_fingerprint_hash"] = hashlib.sha256(json.dumps({"avatar_phash": fp.get("avatar_phash"), "banner_phash": fp.get("banner_phash"), "screenshot_sha256": fp.get("screenshot_sha256")}, sort_keys=True).encode()).hexdigest()
    candidate["evidence_capture"] = capture
    return candidate


def enrich_profile_payload_with_evidence(profile_payload: dict[str, Any], subject_id: int, live_capture_enabled: bool = False) -> dict[str, Any]:
    captured = 0
    asset_only = 0
    text_ready = 0
    visual_ready = 0
    for candidate in profile_payload.get("candidates") or []:
        enrich_candidate_profile_fingerprint(subject_id, candidate, live_capture_enabled=live_capture_enabled)
        fp = candidate.get("profile_fingerprint") or {}
        captured += 1 if fp.get("evidence_capture") else 0
        asset_only += 1 if fp.get("asset_only_url") else 0
        text_ready += 1 if fp.get("display_name") or fp.get("bio_text") or fp.get("linked_urls") else 0
        visual_ready += 1 if fp.get("avatar_phash") or fp.get("banner_phash") or fp.get("screenshot_sha256") else 0
    profile_payload["evidence_capture"] = {
        "schema": SCHEMA,
        "captured_candidate_count": captured,
        "asset_only_candidate_count": asset_only,
        "text_fingerprint_ready_count": text_ready,
        "visual_fingerprint_ready_count": visual_ready,
        "live_capture_enabled": bool(live_capture_enabled),
        "rule": "Analyst acceptance should prefer captured HTML/metadata plus visual/text/link corroboration over username-only matches.",
    }
    return profile_payload
