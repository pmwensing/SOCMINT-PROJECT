from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

SCHEMA = "socmint.social_analyzer_connector.v12_10_2"
DEFAULT_TIMEOUT = 240


def _env_bool(name: str, default: str = "") -> bool:
    return os.environ.get(name, default).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
        "authorized",
    }


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _username_from_target(target: str, target_type: str) -> str:
    value = str(target or "").strip()
    if target_type == "email" and "@" in value:
        return value.split("@", 1)[0]
    return value


def command_for_target(target: str, target_type: str) -> list[str]:
    username = _username_from_target(target, target_type)
    return [
        "social-analyzer",
        "--username",
        username,
        "--metadata",
        "--top",
        "100",
        "--output",
        "json",
    ]


def available() -> bool:
    return shutil.which("social-analyzer") is not None


def run_social_analyzer(
    target: str,
    target_type: str,
    timeout: int = DEFAULT_TIMEOUT,
    allow_dry_run: bool = True,
) -> dict[str, Any]:
    command = command_for_target(target, target_type)
    worker = _env_bool("SOCMINT_WORKER_PROCESS")
    authorized = _env_bool("SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS")
    mode = os.environ.get("SOCMINT_CONNECTOR_MODE", "diagnostic").strip().lower()
    if mode != "real" or not authorized or not worker:
        return {
            "schema": SCHEMA,
            "connector": "social-analyzer",
            "target": target,
            "target_type": target_type,
            "command": command,
            "status": "dry_run",
            "badge": "diagnostic",
            "execution_mode": "diagnostic",
            "returncode": None,
            "stdout": "",
            "stderr": "social-analyzer is deep enrichment and only runs in authorized worker real mode.",
            "started_at": datetime.now(UTC).isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "findings": [],
        }
    if not available():
        if allow_dry_run:
            return {
                "schema": SCHEMA,
                "connector": "social-analyzer",
                "target": target,
                "target_type": target_type,
                "command": command,
                "status": "dry_run",
                "badge": "diagnostic",
                "execution_mode": "diagnostic",
                "returncode": None,
                "stdout": "",
                "stderr": "social-analyzer executable is not installed; rebuild with connector CLIs enabled.",
                "started_at": datetime.now(UTC).isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
                "findings": [],
            }
        raise FileNotFoundError("social-analyzer")

    started = datetime.now(UTC)
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
        finished = datetime.now(UTC)
        payload = {
            "schema": SCHEMA,
            "connector": "social-analyzer",
            "target": target,
            "target_type": target_type,
            "command": command,
            "status": "completed" if result.returncode == 0 else "failed",
            "badge": "real",
            "execution_mode": "real",
            "timeout_seconds": timeout,
            "returncode": result.returncode,
            "stdout": _text(result.stdout),
            "stderr": _text(result.stderr),
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
        }
    except subprocess.TimeoutExpired as exc:
        finished = datetime.now(UTC)
        payload = {
            "schema": SCHEMA,
            "connector": "social-analyzer",
            "target": target,
            "target_type": target_type,
            "command": command,
            "status": "timeout",
            "badge": "real",
            "execution_mode": "real",
            "timeout_seconds": timeout,
            "returncode": None,
            "stdout": _text(exc.stdout),
            "stderr": _text(exc.stderr)
            or f"social-analyzer timed out after {timeout}s",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
        }
    payload["findings"] = _extract_findings(payload)
    return payload


def _extract_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    text = "\n".join([_text(payload.get("stdout")), _text(payload.get("stderr"))])
    try:
        data = json.loads(_text(payload.get("stdout")))
    except Exception:
        data = None
    _walk(data, findings, seen)
    for part in text.split():
        if part.startswith("http://") or part.startswith("https://"):
            value = part.strip().rstrip(",.;)")
            key = ("profile_url", value.lower())
            if key not in seen:
                seen.add(key)
                findings.append(
                    {
                        "type": "profile_url",
                        "value": value,
                        "source": "social-analyzer",
                        "confidence": 0.78,
                        "context": {"deep_enrichment": True},
                    }
                )
    return findings


def _walk(
    data: Any, findings: list[dict[str, Any]], seen: set[tuple[str, str]]
) -> None:
    if isinstance(data, dict):
        url = (
            data.get("url")
            or data.get("link")
            or data.get("profile")
            or data.get("profile_url")
        )
        status = str(
            data.get("status") or data.get("found") or data.get("exists") or ""
        ).lower()
        site = (
            data.get("site")
            or data.get("platform")
            or data.get("name")
            or data.get("website")
        )
        score = data.get("score") or data.get("rating") or data.get("confidence") or 78
        try:
            confidence = max(
                0.5, min(0.95, float(score) / 100 if float(score) > 1 else float(score))
            )
        except Exception:
            confidence = 0.78
        if url and status not in {"false", "not found", "missing", "unknown"}:
            key = ("profile_url", str(url).lower())
            if key not in seen:
                seen.add(key)
                findings.append(
                    {
                        "type": "profile_url",
                        "value": str(url),
                        "source": "social-analyzer",
                        "confidence": confidence,
                        "context": {
                            "platform": site,
                            "status": status,
                            "deep_enrichment": True,
                        },
                    }
                )
        elif site and status in {
            "true",
            "found",
            "exists",
            "registered",
            "used",
            "valid",
        }:
            key = ("platform_presence", str(site).lower())
            if key not in seen:
                seen.add(key)
                findings.append(
                    {
                        "type": "platform_presence",
                        "value": str(site),
                        "source": "social-analyzer",
                        "confidence": confidence,
                        "context": {"status": status, "deep_enrichment": True},
                    }
                )
        for value in data.values():
            _walk(value, findings, seen)
    elif isinstance(data, list):
        for item in data:
            _walk(item, findings, seen)
