from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

from .archivebox_adapter import archivebox_available
from .archivebox_adapter import archivebox_data_dir
from .archivebox_adapter import archivebox_enabled
from .connectors import CONNECTORS
from .connectors import render_command

RUNTIME_SCHEMA = "socmint.connector_runtime.v7_5_9"

VERSION_COMMANDS: dict[str, list[str]] = {
    "sherlock": ["sherlock", "--version"],
    "maigret": ["python", "-m", "maigret", "--version"],
    "socialscan": ["socialscan", "--version"],
    "holehe": ["holehe", "--version"],
    "h8mail": ["h8mail", "--version"],
    "phoneinfoga": ["phoneinfoga", "version"],
}

SAMPLE_TARGETS: dict[str, tuple[str, str]] = {
    "sherlock": ("testuser", "username"),
    "maigret": ("testuser", "username"),
    "socialscan": ("test@example.com", "email"),
    "holehe": ("test@example.com", "email"),
    "h8mail": ("test@example.com", "email"),
    "phoneinfoga": ("+15555550123", "phone"),
}


def _which_for_connector(name: str) -> str | None:
    if name == "maigret":
        if not shutil.which("python"):
            return None
        probe = subprocess.run(
            ["python", "-m", "maigret", "--version"],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        return "python -m maigret" if probe.returncode == 0 else None
    command = VERSION_COMMANDS.get(name) or [name, "--version"]
    return shutil.which(command[0])


def _version_for_connector(name: str, timeout: int = 12) -> dict[str, Any]:
    command = VERSION_COMMANDS.get(name)
    if not command:
        return {"available": False, "version": None, "error": "no version command"}
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        text = (result.stdout or result.stderr or "").strip().splitlines()
        return {
            "available": result.returncode == 0,
            "version": text[0][:160] if text else None,
            "returncode": result.returncode,
            "error": None if result.returncode == 0 else (result.stderr or result.stdout or "version probe failed")[:300],
            "command": command,
        }
    except Exception as exc:
        return {"available": False, "version": None, "error": str(exc), "command": command}


def normalize_connector_output(name: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    text = "\n".join(str(payload.get(key) or "") for key in ("stdout", "stderr"))
    findings = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, value: str, confidence: float = 0.65, context: Any = None) -> None:
        value = str(value or "").strip().rstrip(".,;)")
        if not value:
            return
        key = (kind, value.lower())
        if key in seen:
            return
        seen.add(key)
        item = {"type": kind, "value": value, "source": name, "confidence": confidence}
        if context is not None:
            item["context"] = context
        findings.append(item)

    # Generic URL/email/phone patterns are useful across all tools.
    for value in re.findall(r"https?://[^\s\"'<>]+", text, flags=re.I):
        add("url", value, 0.74)
    for value in re.findall(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text):
        add("email", value, 0.72)
    for value in re.findall(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)", text):
        add("phone", value, 0.58)

    # Try JSON-native outputs.
    for candidate in (payload.get("stdout"), payload.get("raw")):
        try:
            data = json.loads(candidate or "")
        except Exception:
            data = None
        if data is not None:
            _extract_json_findings(name, data, add)

    if name in {"sherlock", "maigret"}:
        for value in re.findall(r"(?i)(?:found|exists|claimed|profile)[:\s-]+(https?://[^\s\"'<>]+)", text):
            add("profile_url", value, 0.78)
    elif name in {"holehe", "h8mail", "socialscan"}:
        for value in re.findall(r"(?i)(?:registered|exists|found|used on)[:\s-]+([A-Za-z0-9_. -]{3,80})", text):
            add("account_presence", value, 0.62)
    elif name == "phoneinfoga":
        for label, value in re.findall(r"(?im)^\s*(carrier|country|line type|number type)\s*[:=]\s*(.+)$", text):
            add("phone_metadata", f"{label}: {value}", 0.66, {"label": label})

    return findings


def _extract_json_findings(name: str, data: Any, add) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            lower_key = str(key).lower()
            if isinstance(value, str):
                if value.startswith("http"):
                    add("url", value, 0.72, {"key": key})
                elif "email" in lower_key and "@" in value:
                    add("email", value, 0.72, {"key": key})
                elif lower_key in {"username", "handle", "user"}:
                    add("username", value, 0.58, {"key": key})
            elif isinstance(value, (dict, list)):
                _extract_json_findings(name, value, add)
    elif isinstance(data, list):
        for item in data:
            _extract_json_findings(name, item, add)


def connector_health(name: str) -> dict[str, Any]:
    if name == "archivebox":
        available = archivebox_available()
        enabled = archivebox_enabled()
        return {
            "name": "archivebox",
            "installed": available,
            "enabled": enabled,
            "status": "ready" if available and enabled else "disabled" if available else "missing",
            "version": None,
            "executable": shutil.which("archivebox"),
            "data_dir": archivebox_data_dir(),
            "sample_command": ["archivebox", "add", "--json", "https://example.com"],
            "target_types": ["url"],
            "notes": "Set SOCMINT_ARCHIVEBOX_ENABLED=true to perform real captures." if not enabled else "ArchiveBox capture enabled.",
        }

    spec = CONNECTORS[name]
    sample_target, sample_type = SAMPLE_TARGETS.get(name, ("test", spec.target_types[0]))
    sample_command = render_command(spec, sample_target, sample_type)
    executable = _which_for_connector(name)
    version = _version_for_connector(name) if executable else {"available": False, "version": None, "error": "executable missing"}
    installed = bool(executable)
    return {
        "name": name,
        "installed": installed,
        "enabled": True,
        "status": "ready" if installed else "missing",
        "version": version.get("version"),
        "version_probe": version,
        "executable": executable,
        "sample_command": sample_command,
        "target_types": list(spec.target_types),
        "timeout": spec.timeout,
        "notes": "Connector will dry-run until the executable is installed." if not installed else "Connector executable detected.",
    }


def connector_runtime_health() -> dict[str, Any]:
    names = sorted(CONNECTORS) + ["archivebox"]
    connectors = [connector_health(name) for name in names]
    counts = {
        "ready": len([item for item in connectors if item["status"] == "ready"]),
        "missing": len([item for item in connectors if item["status"] == "missing"]),
        "disabled": len([item for item in connectors if item["status"] == "disabled"]),
    }
    return {
        "schema": RUNTIME_SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(),
        "dry_run_forced": os.environ.get("SOCMINT_CONNECTOR_DRY_RUN", "").lower() in {"1", "true", "yes", "on"},
        "summary": counts,
        "connectors": connectors,
    }
