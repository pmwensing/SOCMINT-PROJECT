from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

SCHEMA = "socmint.alias_promotion_gates.v12_10_7_1"

ASSET_ONLY_HOSTS = {
    "assets.tumblr.com",
    "tr.rbxcdn.com",
    "rbxcdn.com",
    "simg-ssl.duolingo.com",
    "yt3.googleusercontent.com",
    "googleusercontent.com",
    "p16-common-sign.tiktokcdn.com",
    "tiktokcdn.com",
    "pbs.twimg.com",
    "s.pinimg.com",
    "pinimg.com",
    "web.static.mmcdn.com",
    "mmcdn.com",
    "avatars.githubusercontent.com",
    "github.githubassets.com",
}

ASSET_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".avif",
    ".css",
    ".js",
)

ASSET_PATH_HINTS = (
    "avatar",
    "avatars",
    "profile_images",
    "images",
    "image",
    "img",
    "favicon",
    "favicons",
    "logo",
    "logos",
    "static",
    "assets",
    "asset",
    "cdn",
    "webapp",
    "manifest",
    "mstile",
    "default_avatar",
    "cropcenter",
    "ssr-avatar",
    "ssr_",
    "ytc/",
    "30day-avatar",
)

PHONE_MIN_DIGITS = 10
PHONE_MAX_DIGITS = 15


def norm(value: Any) -> str:
    return str(value or "").strip()


def domain_for_url(url: Any) -> str:
    value = norm(url).lower().replace("\ufffe", "-")
    parsed = urlparse(value)
    return (parsed.netloc or parsed.path.split("/", 1)[0]).removeprefix("www.")


def is_asset_only_url(url: Any) -> bool:
    value = norm(url).lower().replace("\ufffe", "-")
    if not value:
        return False
    parsed = urlparse(value)
    host = domain_for_url(value)
    path = parsed.path.lower()
    host_match = any(
        host == item or host.endswith("." + item) for item in ASSET_ONLY_HOSTS
    )
    ext_match = any(
        path.endswith(ext) or f"{ext}?" in value for ext in ASSET_EXTENSIONS
    )
    hint_match = any(hint in path for hint in ASSET_PATH_HINTS)
    return (host_match and (ext_match or hint_match)) or (ext_match and hint_match)


def classify_asset_url(url: Any) -> str:
    value = norm(url).lower().replace("\ufffe", "-")
    if not is_asset_only_url(value):
        return "profile_url"
    path = urlparse(value).path.lower()
    if any(
        token in path
        for token in ("avatar", "profile_images", "ytc/", "30day-avatar", "ssr-avatar")
    ):
        return "avatar_url"
    return "static_asset_url"


def is_timestamp_like(value: Any) -> bool:
    text = norm(value)
    if re.search(r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2})?\b", text):
        return True
    digits = re.sub(r"\D+", "", text)
    if digits.isdigit() and len(digits) == 10:
        number = int(digits)
        return 946684800 <= number <= 4102444800
    return False


def is_float_like(value: Any) -> bool:
    return bool(re.fullmatch(r"\d+\.\d+", norm(value)))


def is_platform_artifact_id(value: Any) -> bool:
    text = norm(value)
    digits = re.sub(r"\D+", "", text)
    if not digits:
        return False
    if len(digits) > PHONE_MAX_DIGITS:
        return True
    if len(digits) < PHONE_MIN_DIGITS:
        return True
    if re.fullmatch(r"\d+", text) and len(digits) in {10, 13}:
        return True
    return False


def phone_rejection_reason(value: Any) -> str | None:
    if is_float_like(value):
        return "rejected_not_phone"
    if is_timestamp_like(value):
        return "rejected_timestamp"
    if is_platform_artifact_id(value):
        return "rejected_platform_artifact_id"
    return None


def classify_observation_type(
    observation_type: str, value: Any
) -> tuple[str, list[str], bool]:
    reasons: list[str] = []
    otype = norm(observation_type)
    if otype in {"profile_url", "url"} and is_asset_only_url(value):
        reasons.append("rejected_asset_only_url")
        return classify_asset_url(value), reasons, True
    if otype == "phone":
        reason = phone_rejection_reason(value)
        if reason:
            reasons.append(reason)
            safe_type = (
                "platform_artifact_id"
                if reason == "rejected_platform_artifact_id"
                else "metadata_artifact"
            )
            return safe_type, reasons, True
    return otype, reasons, False


def promotion_gate_for_observation(observation: dict[str, Any]) -> dict[str, Any]:
    value = observation.get("value") or observation.get("normalized_value")
    otype = observation.get("type") or observation.get("observation_type")
    converted_type, reasons, blocked = classify_observation_type(str(otype), value)
    return {
        "schema": SCHEMA,
        "blocked": blocked,
        "original_type": otype,
        "safe_type": converted_type,
        "reason_labels": reasons,
        "ui_badge": "Promotion blocked: not identity evidence"
        if blocked
        else "Promotion allowed",
    }


def apply_promotion_gates_to_observation(observation: dict[str, Any]) -> dict[str, Any]:
    gate = promotion_gate_for_observation(observation)
    observation["promotion_gate"] = gate
    observation["promotion_blocked"] = gate["blocked"]
    observation["promotion_block_reason_labels"] = gate["reason_labels"]
    if gate["blocked"]:
        observation["type"] = gate["safe_type"]
        payload = observation.setdefault("payload", {})
        payload["promotion_gate"] = gate
    return observation


def apply_promotion_gates_to_alias(alias: dict[str, Any]) -> dict[str, Any]:
    gate = {
        "schema": SCHEMA,
        "blocked": False,
        "reason_labels": [],
        "ui_badge": "Promotion allowed",
    }
    alias_type = norm(alias.get("alias_type"))
    value = alias.get("normalized_value") or alias.get("alias_value")

    if alias_type == "url" and is_asset_only_url(value):
        gate.update(
            {
                "blocked": True,
                "reason_labels": ["rejected_asset_only_url"],
                "ui_badge": "Promotion blocked: not identity evidence",
                "safe_type": classify_asset_url(value),
            }
        )
    elif alias_type == "phone":
        reason = phone_rejection_reason(value)
        if reason:
            gate.update(
                {
                    "blocked": True,
                    "reason_labels": [reason],
                    "ui_badge": "Promotion blocked: not identity evidence",
                    "safe_type": "metadata_artifact",
                }
            )

    alias["promotion_gate"] = gate
    if gate["blocked"]:
        alias["analyst_state"] = "rejected"
        alias["can_promote_to_dossier_assertion"] = False
        alias.setdefault("negative_reasons", [])
        for reason in gate["reason_labels"]:
            if reason not in alias["negative_reasons"]:
                alias["negative_reasons"].append(reason)
    return alias


def apply_promotion_gates_to_alias_graph(alias_graph: dict[str, Any]) -> dict[str, Any]:
    blocked = 0
    reasons: dict[str, int] = {}
    for alias in alias_graph.get("aliases") or []:
        apply_promotion_gates_to_alias(alias)
        gate = alias.get("promotion_gate", {})
        if gate.get("blocked"):
            blocked += 1
            for reason in gate.get("reason_labels") or []:
                reasons[reason] = reasons.get(reason, 0) + 1

    alias_graph["promotion_gates"] = {
        "schema": SCHEMA,
        "blocked_alias_count": blocked,
        "reason_counts": reasons,
        "rule": "Asset/CDN URLs and non-phone numeric artifacts cannot be promoted as identity evidence.",
    }
    return alias_graph
