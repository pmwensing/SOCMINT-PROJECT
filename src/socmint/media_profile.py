import json
import mimetypes
import shutil
import subprocess
from datetime import datetime, UTC
from pathlib import Path
from urllib.parse import urlparse

from .artifacts import sha256_bytes, write_json_artifact


PROFILE_KEYS = {
    "display_name",
    "username",
    "bio",
    "avatar_url",
    "profile_url",
    "platform",
}


def classify_url(url: str) -> str:
    parsed = urlparse(url or "")
    path = parsed.path.lower()
    if path.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov")):
        return "media"
    return "profile"


def normalize_profile_payload(payload: dict) -> dict:
    return {
        "display_name": payload.get("display_name") or payload.get("title"),
        "username": payload.get("username") or payload.get("handle"),
        "bio": payload.get("bio") or payload.get("description"),
        "avatar_url": payload.get("avatar_url") or payload.get("image"),
        "profile_url": payload.get("profile_url") or payload.get("url"),
        "platform": payload.get("platform") or infer_platform(payload.get("url", "")),
        "raw": payload,
    }


def infer_platform(url: str) -> str | None:
    parsed = urlparse(url or "")
    host = parsed.netloc.lower()
    if not host:
        return None
    return host.replace("www.", "")


def enrich_profile_url(url: str, metadata: dict | None = None) -> dict:
    metadata = metadata or {}
    payload = normalize_profile_payload({"url": url, **metadata})
    artifact = write_json_artifact(
        "profile-enrichment",
        payload,
        prefix="profile",
    )
    findings = []

    for key in PROFILE_KEYS:
        value = payload.get(key)
        if value:
            findings.append(
                {
                    "type": f"profile_{key}",
                    "value": str(value),
                    "source": "profile_enrichment",
                    "confidence": 0.66,
                    "context": {"profile_url": url, "artifact": artifact},
                }
            )

    return {
        "adapter": "profile_enrichment",
        "status": "completed",
        "url": url,
        "profile": payload,
        "artifact": artifact,
        "findings": findings,
        "created_at": datetime.now(UTC).isoformat(),
    }


def enrich_media_path(path: str, source_url: str | None = None) -> dict:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(path)

    data = file_path.read_bytes()
    digest = sha256_bytes(data)
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    exif = extract_exif_metadata(file_path)

    payload = {
        "path": str(file_path),
        "source_url": source_url,
        "sha256": digest,
        "mime_type": mime_type,
        "size_bytes": len(data),
        "exif": exif,
    }
    artifact = write_json_artifact("media-enrichment", payload, prefix="media")

    findings = [
        {
            "type": "media_asset",
            "value": source_url or str(file_path),
            "source": "media_enrichment",
            "confidence": 0.72,
            "context": {
                "sha256": digest,
                "mime_type": mime_type,
                "size_bytes": len(data),
                "artifact": artifact,
            },
        }
    ]

    if exif.get("status") == "completed":
        findings.append(
            {
                "type": "media_metadata",
                "value": digest,
                "source": "exiftool",
                "confidence": 0.76,
                "context": exif,
            }
        )

    return {
        "adapter": "media_enrichment",
        "status": "completed",
        "media": payload,
        "artifact": artifact,
        "findings": findings,
        "created_at": datetime.now(UTC).isoformat(),
    }


def extract_exif_metadata(path: Path) -> dict:
    if shutil.which("exiftool") is None:
        return {
            "status": "dry_run",
            "reason": "exiftool executable is not installed.",
        }

    command = ["exiftool", "-json", str(path)]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "command": command}

    payload = {
        "status": "completed" if result.returncode == 0 else "failed",
        "command": command,
        "returncode": result.returncode,
        "stderr": result.stderr,
        "metadata": [],
    }

    try:
        parsed = json.loads(result.stdout or "[]")
        if isinstance(parsed, list):
            payload["metadata"] = parsed
    except json.JSONDecodeError:
        payload["metadata"] = []

    return payload


def enrich_url_observation(url: str) -> dict:
    kind = classify_url(url)
    if kind == "media":
        return {
            "adapter": "media_enrichment",
            "status": "dry_run",
            "url": url,
            "reason": "Remote media download is not enabled in v6.4.",
            "findings": [
                {
                    "type": "media_url",
                    "value": url,
                    "source": "media_enrichment",
                    "confidence": 0.58,
                    "context": {"remote_download_enabled": False},
                }
            ],
        }
    return enrich_profile_url(url)
