from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .artifacts import artifact_root

SCHEMA = "socmint.profile_evidence_capture.v12_10_5_1"
CAPTURE_VERSION = "12.10.5.1"
ROUTE_PLACEHOLDER_USERNAMES = {"people", "perfil", "accounts", "account", "add", "user", "users", "profile", "profiles", "members", "member", "unknown", "unknown username", "images", "webapp", "favicons", "pop", "ytc", "ssr-avatars"}
PROFILE_PATH_HINTS = {"user", "users", "profile", "profiles", "u", "people", "person", "perfil", "accounts", "account", "add", "members", "member", "@"}
USERNAME_QUERY_KEYS = ("username", "user", "handle")
ASSET_ONLY_DOMAINS = {
    "gravatar.com",
    "secure.gravatar.com",
    "avatars.githubusercontent.com",
    "github.githubassets.com",
    "static.xx.fbcdn.net",
    "pbs.twimg.com",
    "abs.twimg.com",
    "cdn.discordapp.com",
    "tr.rbxcdn.com",
    "rbxcdn.com",
    "simg-ssl.duolingo.com",
    "duolingo.com",
    "yt3.googleusercontent.com",
    "googleusercontent.com",
    "p16-common-sign.tiktokcdn.com",
    "tiktokcdn.com",
    "s.pinimg.com",
    "pinimg.com",
    "assets.tumblr.com",
    "tumblr.com",
    "web.static.mmcdn.com",
    "mmcdn.com",
}
ASSET_DOMAIN_PATH_HINTS = {
    "avatar", "avatars", "profile_images", "images", "image", "img", "favicon", "favicons", "logo", "logos", "static", "assets", "asset", "cdn", "webapp", "manifest", "mstile", "default_avatar", "ssr-avatars", "ytc", "30day", "cropcenter"
}
NON_PROFILE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".css", ".js", ".avif"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _norm(value).lower()


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


def _query_username(parsed) -> str:
    query = parse_qs(parsed.query or "")
    for key in USERNAME_QUERY_KEYS:
        values = query.get(key) or []
        if values and _norm(values[0]):
            return _norm(values[0]).lstrip("@")
    return ""


def enhanced_username_from_url(url: str) -> str:
    parsed = urlparse(_norm(url))
    query_username = _query_username(parsed)
    if query_username:
        return query_username
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


def username_needs_rewrite(username: Any) -> bool:
    return _lower(username) in ROUTE_PLACEHOLDER_USERNAMES or not _norm(username)


def canonical_profile_username(existing_username: Any, profile_url: str) -> str:
    parsed_username = enhanced_username_from_url(profile_url)
    if username_needs_rewrite(existing_username) and parsed_username:
        return parsed_username
    return _norm(existing_username) or parsed_username


def is_asset_only_url(url: str) -> bool:
    value = _norm(url).lower().replace("\ufffe", "-")
    if not value:
        return False
    domain = domain_for_url(value)
    parsed = urlparse(value)
    path = parsed.path.lower()
    path_tokens = {token for token in re.split(r"[^a-z0-9]+", path) if token}
    has_asset_domain = any(domain == item or domain.endswith("." + item) for item in ASSET_ONLY_DOMAINS)
    has_asset_ext = any(path.endswith(ext) or f"{ext}?" in value for ext in NON_PROFILE_EXTENSIONS)
    has_asset_hint = bool(path_tokens.intersection(ASSET_DOMAIN_PATH_HINTS)) or any(hint in path for hint in ("/avatar", "favicon", "logo", "profile_images", "default_avatar", "cropcenter"))
    if has_asset_domain and (has_asset_ext or has_asset_hint):
        return True
    return has_asset_ext and has_asset_hint


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
        "username": canonical_profile_username(fp.get("username"), profile_url),
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


def suppress_asset_only_candidate(candidate: dict[str, Any]) -> None:
    fp = candidate.get("profile_fingerprint") or {}
    if not fp.get("asset_only_url"):
        return
    candidate["identity_score"] = min(float(candidate.get("identity_score") or 0.0), 0.05)
    candidate["collision_status"] = "asset_only_not_profile"
    candidate.setdefault("negative_reasons", [])
    if "asset/CDN URL is not a profile page; excluded from identity-link assertion" not in candidate["negative_reasons"]:
        candidate["negative_reasons"].append("asset/CDN URL is not a profile page; excluded from identity-link assertion")
    candidate.setdefault("identity_link_hypothesis", {})
    candidate["identity_link_hypothesis"].update({
        "relationship": "candidate_asset_only_not_profile",
        "confidence": candidate["identity_score"],
        "can_promote_to_dossier_assertion": False,
        "dossier_language": "Asset/CDN URL only; do not treat as a profile identity assertion.",
    })
    candidate.setdefault("dossier_assertion_gate", {})
    candidate["dossier_assertion_gate"].update({
        "stage": "dossier_assertion",
        "dossier_ready": False,
        "assertion_type": "asset_only_profile_suppressed",
        "blocked_reason": "Asset/CDN URL is not a profile page and is suppressed from profile_url dossier assertions.",
        "suppressed": True,
    })
    candidate["dossier_ready"] = False


def enrich_candidate_profile_fingerprint(subject_id: int, candidate: dict[str, Any], live_capture_enabled: bool = False) -> dict[str, Any]:
    fp = candidate.setdefault("profile_fingerprint", {})
    profile_url = _norm(fp.get("profile_url"))
    context = candidate.get("context") if isinstance(candidate.get("context"), dict) else {}
    fp["username"] = canonical_profile_username(fp.get("username"), profile_url)
    linked_urls = sorted(set((fp.get("linked_urls") or []) + _extract_linked_urls(context, profile_url)))
    fp["linked_urls"] = linked_urls
    if context.get("banner_url") and not fp.get("banner_url"):
        fp["banner_url"] = _norm(context.get("banner_url"))
    if fp.get("avatar_url") and not fp.get("avatar_phash"):
        fp["avatar_phash"] = _stable_phash(fp["avatar_url"])
    if fp.get("banner_url") and not fp.get("banner_phash"):
        fp["banner_phash"] = _stable_phash(fp["banner_url"])
    fp["asset_only_url"] = is_asset_only_url(profile_url)
    capture = capture_candidate_profile_artifacts(subject_id, candidate, live_capture_enabled=live_capture_enabled)
    fp["evidence_capture"] = capture
    fp["html_sha256"] = capture["files"]["html"]["sha256"]
    fp["screenshot_sha256"] = capture["files"]["screenshot"]["sha256"]
    fp["metadata_sha256"] = capture["files"]["metadata"]["sha256"]
    fp["text_fingerprint_hash"] = hashlib.sha256(json.dumps({"display_name": fp.get("display_name"), "bio_text": fp.get("bio_text"), "location": fp.get("location"), "linked_urls": linked_urls}, sort_keys=True).encode()).hexdigest()
    fp["visual_fingerprint_hash"] = hashlib.sha256(json.dumps({"avatar_phash": fp.get("avatar_phash"), "banner_phash": fp.get("banner_phash"), "screenshot_sha256": fp.get("screenshot_sha256")}, sort_keys=True).encode()).hexdigest()
    candidate["evidence_capture"] = capture
    suppress_asset_only_candidate(candidate)
    return candidate


def enrich_profile_payload_with_evidence(profile_payload: dict[str, Any], subject_id: int, live_capture_enabled: bool = False) -> dict[str, Any]:
    captured = 0
    asset_only = 0
    text_ready = 0
    visual_ready = 0
    suppressed = 0
    rewritten = 0
    for candidate in profile_payload.get("candidates") or []:
        old_username = _norm((candidate.get("profile_fingerprint") or {}).get("username"))
        enrich_candidate_profile_fingerprint(subject_id, candidate, live_capture_enabled=live_capture_enabled)
        fp = candidate.get("profile_fingerprint") or {}
        captured += 1 if fp.get("evidence_capture") else 0
        asset_only += 1 if fp.get("asset_only_url") else 0
        suppressed += 1 if candidate.get("dossier_assertion_gate", {}).get("suppressed") else 0
        rewritten += 1 if old_username != _norm(fp.get("username")) else 0
        text_ready += 1 if fp.get("display_name") or fp.get("bio_text") or fp.get("linked_urls") else 0
        visual_ready += 1 if fp.get("avatar_phash") or fp.get("banner_phash") or fp.get("screenshot_sha256") else 0
    profile_payload["evidence_capture"] = {
        "schema": SCHEMA,
        "captured_candidate_count": captured,
        "asset_only_candidate_count": asset_only,
        "suppressed_asset_only_assertion_count": suppressed,
        "rewritten_username_count": rewritten,
        "text_fingerprint_ready_count": text_ready,
        "visual_fingerprint_ready_count": visual_ready,
        "live_capture_enabled": bool(live_capture_enabled),
        "rule": "Analyst acceptance should prefer captured HTML/metadata plus visual/text/link corroboration over username-only matches. Asset/CDN URLs are suppressed from profile_url dossier assertions.",
    }
    return profile_payload
