import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass(frozen=True)
class ConnectorSpec:
    name: str
    target_types: tuple[str, ...]
    command: tuple[str, ...]
    timeout: int = 300


CONNECTORS = {
    "sherlock": ConnectorSpec(
        name="sherlock",
        target_types=("username", "email"),
        command=("sherlock", "{username}"),
    ),
    "holehe": ConnectorSpec(
        name="holehe",
        target_types=("email",),
        command=("holehe", "{email}"),
    ),
    "maigret": ConnectorSpec(
        name="maigret",
        target_types=("username", "email"),
        command=("python", "-m", "maigret", "{username}", "--json"),
    ),
    "h8mail": ConnectorSpec(
        name="h8mail",
        target_types=("email",),
        command=("h8mail", "-t", "{email}", "-j"),
    ),
    "socialscan": ConnectorSpec(
        name="socialscan",
        target_types=("username", "email"),
        command=("socialscan", "{target}"),
    ),
    "phoneinfoga": ConnectorSpec(
        name="phoneinfoga",
        target_types=("phone",),
        command=("phoneinfoga", "scan", "-n", "{phone}"),
    ),
}


def list_connectors():
    return [
        {
            "name": spec.name,
            "target_types": list(spec.target_types),
            "command": list(spec.command),
            "timeout": spec.timeout,
        }
        for spec in CONNECTORS.values()
    ]


def split_target(target, target_type):
    if target_type == "email" and "@" in target:
        username, domain = target.split("@", 1)
        return {
            "target": target,
            "email": target,
            "username": username,
            "domain": domain,
        }
    return {
        "target": target,
        "email": target,
        "username": target,
        "domain": target,
        "phone": target,
    }


def render_command(spec, target, target_type):
    values = split_target(target, target_type)
    return [part.format(**values) for part in spec.command]


def executable_available(command):
    if not command:
        return False
    if command[0] == "python" and len(command) >= 3 and command[1] == "-m":
        return shutil.which("python") is not None
    return shutil.which(command[0]) is not None


def connector_dry_run_forced():
    value = os.environ.get("SOCMINT_CONNECTOR_DRY_RUN", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def dry_run_payload(name, target, target_type, command):
    return {
        "connector": name,
        "target": target,
        "target_type": target_type,
        "command": command,
        "status": "dry_run",
        "returncode": None,
        "stdout": "",
        "stderr": f"{name} executable is not installed; dry-run recorded instead.",
        "started_at": datetime.now(UTC).isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "findings": [],
    }


def run_connector(name, target, target_type, allow_dry_run=True):
    if name not in CONNECTORS:
        raise ValueError(f"Unknown connector: {name}")

    spec = CONNECTORS[name]
    if target_type not in spec.target_types:
        return {
            "connector": name,
            "target": target,
            "target_type": target_type,
            "status": "skipped",
            "returncode": None,
            "stdout": "",
            "stderr": f"{name} does not support target type {target_type}",
            "findings": [],
        }

    command = render_command(spec, target, target_type)
    if allow_dry_run and connector_dry_run_forced():
        return dry_run_payload(name, target, target_type, command)

    if not executable_available(command):
        if allow_dry_run:
            return dry_run_payload(name, target, target_type, command)
        raise FileNotFoundError(command[0])

    started = datetime.now(UTC)
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=spec.timeout,
            check=False,
        )
        finished = datetime.now(UTC)
        payload = {
            "connector": name,
            "target": target,
            "target_type": target_type,
            "command": command,
            "status": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
        }
        payload["findings"] = extract_findings(name, payload)
        return payload
    except subprocess.TimeoutExpired as exc:
        finished = datetime.now(UTC)
        payload = {
            "connector": name,
            "target": target,
            "target_type": target_type,
            "command": command,
            "status": "timeout",
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"{name} timed out",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "findings": [],
        }
        return payload


def extract_findings(connector_name, payload):
    text = "\n".join(
        str(payload.get(key) or "") for key in ("stdout", "stderr")
    )
    findings = []

    url_pattern = re.compile(r"https?://[^\s\"'<>]+", re.I)
    email_pattern = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}")
    username_pattern = re.compile(
    r"(?i)(?:username|user|handle)[:=]\\s*([a-z0-9_.-]{3,})"
)

    seen = set()

    for match in url_pattern.findall(text):
        value = match.rstrip(".,;)")
        key = ("url", value)
        if key not in seen:
            seen.add(key)
            findings.append(
                {
                    "type": "url",
                    "value": value,
                    "source": connector_name,
                    "confidence": 0.75,
                }
            )

    for match in email_pattern.findall(text):
        key = ("email", match)
        if key not in seen:
            seen.add(key)
            findings.append(
                {
                    "type": "email",
                    "value": match,
                    "source": connector_name,
                    "confidence": 0.7,
                }
            )

    for match in username_pattern.findall(text):
        key = ("username", match)
        if key not in seen:
            seen.add(key)
            findings.append(
                {
                    "type": "username",
                    "value": match,
                    "source": connector_name,
                    "confidence": 0.55,
                }
            )

    if not findings:
        # Try JSON-native connector output.
        try:
            data = json.loads(payload.get("stdout") or "{}")
        except json.JSONDecodeError:
            data = None

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and value.startswith("http"):
                    findings.append(
                        {
                            "type": "url",
                            "value": value,
                            "source": connector_name,
                            "confidence": 0.7,
                            "context": key,
                        }
                    )

    return findings
