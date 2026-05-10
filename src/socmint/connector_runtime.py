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

RUNTIME_SCHEMA = "socmint.connector_runtime.v7_6_1"

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

NATIVE_DEPENDENCIES = {
    "pkg-config": "pkg-config",
    "cmake": "cmake",
    "gcc/cc": "cc",
}

NATIVE_DEPENDENCY_INSTALL = (
    "sudo apt update && sudo apt install -y pkg-config cmake build-essential "
    "python3-dev libcairo2-dev libgirepository-2.0-dev gir1.2-gtk-3.0"
)

INSTALL_HINTS: dict[str, dict[str, Any]] = {
    "maigret": {
        "install_command": "python -m pip install --upgrade maigret",
        "check_command": "python -m maigret --version",
        "runtime_note": "Python module connector. If pycairo/cairo fails, install native deps: " + NATIVE_DEPENDENCY_INSTALL,
        "native_dependency_hint": NATIVE_DEPENDENCY_INSTALL,
    },
    "sherlock": {
        "install_command": "python -m pip install --upgrade sherlock-project",
        "check_command": "sherlock --version || python -m sherlock --help",
        "runtime_note": "Package/executable naming varies by distribution; health check looks for the sherlock CLI.",
    },
    "socialscan": {
        "install_command": "python -m pip install --upgrade socialscan",
        "check_command": "socialscan --version",
        "runtime_note": "Python CLI connector for username/email account checks.",
    },
    "holehe": {
        "install_command": "python -m pip install --upgrade holehe",
        "check_command": "holehe --version || holehe --help",
        "runtime_note": "Python CLI connector for email account presence checks.",
    },
    "h8mail": {
        "install_command": "python -m pip install --upgrade h8mail",
        "check_command": "h8mail --version || h8mail -h",
        "runtime_note": "Python CLI connector for email exposure checks.",
    },
    "phoneinfoga": {
        "install_command": "Download/install PhoneInfoga binary, then ensure phoneinfoga is on PATH.",
        "check_command": "phoneinfoga version || phoneinfoga --help",
        "runtime_note": "Binary connector; v7.6.1 shows manual activation guidance.",
        "manual_steps": [
            "mkdir -p .connector-tools/bin",
            "Download the official PhoneInfoga Linux binary for your CPU architecture.",
            "Place it at .connector-tools/bin/phoneinfoga",
            "chmod +x .connector-tools/bin/phoneinfoga",
            "source .connector-tools/bin/socmint-connectors-env",
            "phoneinfoga version || phoneinfoga --help",
        ],
    },
    "archivebox": {
        "install_command": "python -m pip install --upgrade archivebox && export SOCMINT_ARCHIVEBOX_ENABLED=true",
        "check_command": "archivebox version || archivebox --version",
        "runtime_note": "Heavy optional connector. Requires SOCMINT_ARCHIVEBOX_ENABLED=true before real captures are attempted. If pycairo/cairo fails, install native deps: " + NATIVE_DEPENDENCY_INSTALL,
        "native_dependency_hint": NATIVE_DEPENDENCY_INSTALL,
    },
}


def native_dependency_status() -> dict[str, Any]:
    items = []
    missing = []
    for label, executable in NATIVE_DEPENDENCIES.items():
        path = shutil.which(executable)
        ok = bool(path)
        items.append({"name": label, "executable": executable, "path": path, "available": ok})
        if not ok:
            missing.append(label)
    cairo_probe = subprocess.run(
        ["pkg-config", "--exists", "cairo"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    ) if shutil.which("pkg-config") else None
    cairo_available = bool(cairo_probe and cairo_probe.returncode == 0)
    items.append({"name": "cairo", "executable": "pkg-config --exists cairo", "path": None, "available": cairo_available})
    if not cairo_available:
        missing.append("cairo")
    return {
        "items": items,
        "missing": missing,
        "ready": not missing,
        "install_command": NATIVE_DEPENDENCY_INSTALL,
        "why": "Needed when pycairo/cairo is pulled by Maigret or ArchiveBox dependencies.",
    }


def install_hint(name: str) -> dict[str, Any]:
    return INSTALL_HINTS.get(name, {
        "install_command": "No installer hint available.",
        "check_command": f"{name} --version",
        "runtime_note": "Unknown connector install profile.",
    })


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

    for value in re.findall(r"https?://[^\s\"'<>]+", text, flags=re.I):
        add("url", value, 0.74)
    for value in re.findall(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text):
        add("email", value, 0.72)
    for value in re.findall(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)", text):
        add("phone", value, 0.58)

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
    hint = install_hint(name)
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
            "install_hint": hint,
            "install_command": hint["install_command"],
            "check_command": hint["check_command"],
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
        "install_hint": hint,
        "install_command": hint["install_command"],
        "check_command": hint["check_command"],
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
        "native_dependencies": native_dependency_status(),
        "installer": {
            "script": "scripts/install_connector_runtime_v7_6_0.sh",
            "scanner_compose": "docker-compose.scanners.yml",
            "health_command": "make connectors-health",
        },
    }
