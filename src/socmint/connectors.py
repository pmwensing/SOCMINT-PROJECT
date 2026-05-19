import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class ConnectorSpec:
    name: str
    target_types: tuple[str, ...]
    command: tuple[str, ...]
    timeout: int = 45


CONNECTORS = {
    "sherlock": ConnectorSpec(name="sherlock", target_types=("username", "email"), command=("sherlock", "{username}"), timeout=75),
    "holehe": ConnectorSpec(name="holehe", target_types=("email",), command=("holehe", "{email}"), timeout=45),
    "maigret": ConnectorSpec(name="maigret", target_types=("username", "email"), command=("python", "-m", "maigret", "{username}", "-J", "simple", "--timeout", "15"), timeout=60),
    "h8mail": ConnectorSpec(name="h8mail", target_types=("email",), command=("h8mail", "-t", "{email}", "-j"), timeout=60),
    "socialscan": ConnectorSpec(name="socialscan", target_types=("username", "email"), command=("socialscan", "{target}"), timeout=45),
    "phoneinfoga": ConnectorSpec(name="phoneinfoga", target_types=("phone",), command=("phoneinfoga", "scan", "-n", "{phone}"), timeout=45),
}


def list_connectors():
    return [{"name": spec.name, "target_types": list(spec.target_types), "command": list(spec.command), "timeout": spec.timeout} for spec in CONNECTORS.values()]


def _env_bool(name: str, default: str = "") -> bool:
    value = os.environ.get(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on", "authorized"}


def connector_execution_mode() -> str:
    mode = os.environ.get("SOCMINT_CONNECTOR_MODE") or os.environ.get("SOCMINT_CONNECTOR_EXECUTION_MODE") or "diagnostic"
    mode = mode.strip().lower().replace("_", "-")
    if mode in {"real", "live", "real-world", "realworld"}:
        return "real"
    if mode in {"dry-run", "dryrun", "dry"}:
        return "dry-run"
    return "diagnostic"


def real_world_connectors_authorized() -> bool:
    return _env_bool("SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS")


def connector_worker_process() -> bool:
    return _env_bool("SOCMINT_WORKER_PROCESS")


def allow_web_real_connectors() -> bool:
    return _env_bool("SOCMINT_ALLOW_WEB_REAL_CONNECTORS")


def connector_mode_report() -> dict:
    mode = connector_execution_mode()
    authorized = real_world_connectors_authorized()
    worker = connector_worker_process()
    allow_web_real = allow_web_real_connectors()
    effective = "diagnostic"
    reason = "Default diagnostic mode; real connector execution is disabled."
    if mode == "dry-run":
        effective = "dry-run"
        reason = "Dry-run mode requested."
    elif mode == "real" and not authorized:
        effective = "diagnostic"
        reason = "Real mode requested but SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS is not true."
    elif mode == "real" and authorized and not worker and not allow_web_real:
        effective = "diagnostic"
        reason = "Real mode is worker-only by default; web process is protected from blocking connector subprocesses."
    elif mode == "real" and authorized:
        effective = "real"
        reason = "Real connector execution enabled for authorized worker/runtime."
    return {
        "schema": "socmint.connector_execution_mode.v12_10_1",
        "requested_mode": mode,
        "authorized_realworld_connectors": authorized,
        "worker_process": worker,
        "allow_web_real_connectors": allow_web_real,
        "effective_mode": effective,
        "real_world_enabled": effective == "real",
        "reason": reason,
        "safety_note": "Real connector execution requires SOCMINT_CONNECTOR_MODE=real, SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS=true, and worker process context unless SOCMINT_ALLOW_WEB_REAL_CONNECTORS=true.",
    }


def split_target(target, target_type):
    if target_type == "email" and "@" in target:
        username, domain = target.split("@", 1)
        return {"target": target, "email": target, "username": username, "domain": domain}
    return {"target": target, "email": target, "username": target, "domain": target, "phone": target}


def render_command(spec, target, target_type):
    values = split_target(target, target_type)
    return [part.format(**values) for part in spec.command]


def executable_available(command):
    if not command:
        return False
    if command[0] == "python" and len(command) >= 3 and command[1] == "-m":
        return shutil.which("python") is not None or shutil.which("python3") is not None
    return shutil.which(command[0]) is not None


def connector_dry_run_forced():
    return _env_bool("SOCMINT_CONNECTOR_DRY_RUN")


def _with_normalized_findings(name, payload):
    try:
        from .connector_runtime import normalize_connector_output
        payload["findings"] = normalize_connector_output(name, payload)
    except Exception:
        payload["findings"] = extract_findings(name, payload)
    return payload


def dry_run_payload(name, target, target_type, command, reason=None, mode="dry-run"):
    payload = {"connector": name, "target": target, "target_type": target_type, "command": command, "status": "dry_run", "badge": "diagnostic" if mode == "diagnostic" else "dry-run", "execution_mode": mode, "returncode": None, "stdout": "", "stderr": reason or f"{name} executable is not installed; dry-run recorded instead.", "started_at": datetime.now(UTC).isoformat(), "finished_at": datetime.now(UTC).isoformat()}
    return _with_normalized_findings(name, payload)


def run_connector(name, target, target_type, allow_dry_run=True):
    if name not in CONNECTORS:
        raise ValueError(f"Unknown connector: {name}")
    spec = CONNECTORS[name]
    if target_type not in spec.target_types:
        return _with_normalized_findings(name, {"connector": name, "target": target, "target_type": target_type, "status": "skipped", "execution_mode": connector_mode_report()["effective_mode"], "returncode": None, "stdout": "", "stderr": f"{name} does not support target type {target_type}"})
    command = render_command(spec, target, target_type)
    mode = connector_mode_report()
    effective_mode = mode["effective_mode"]
    if connector_dry_run_forced():
        return dry_run_payload(name, target, target_type, command, reason="SOCMINT_CONNECTOR_DRY_RUN is enabled; dry-run recorded instead.", mode="dry-run")
    if effective_mode != "real":
        return dry_run_payload(name, target, target_type, command, reason=mode.get("reason"), mode=effective_mode)
    if not executable_available(command):
        if allow_dry_run:
            return dry_run_payload(name, target, target_type, command, reason=f"{name} executable is not installed; real mode requested but dry-run fallback recorded.", mode="dry-run")
        raise FileNotFoundError(command[0])
    started = datetime.now(UTC)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=spec.timeout, check=False)
        finished = datetime.now(UTC)
        payload = {"connector": name, "target": target, "target_type": target_type, "command": command, "status": "completed" if result.returncode == 0 else "failed", "badge": "real", "execution_mode": "real", "timeout_seconds": spec.timeout, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "started_at": started.isoformat(), "finished_at": finished.isoformat()}
        return _with_normalized_findings(name, payload)
    except subprocess.TimeoutExpired as exc:
        finished = datetime.now(UTC)
        payload = {"connector": name, "target": target, "target_type": target_type, "command": command, "status": "timeout", "badge": "real", "execution_mode": "real", "timeout_seconds": spec.timeout, "returncode": None, "stdout": exc.stdout or "", "stderr": exc.stderr or f"{name} timed out after {spec.timeout}s", "started_at": started.isoformat(), "finished_at": finished.isoformat()}
        return _with_normalized_findings(name, payload)


def extract_findings(connector_name, payload):
    text = "\n".join(str(payload.get(key) or "") for key in ("stdout", "stderr"))
    findings = []
    url_pattern = re.compile(r"https?://[^\s\"'<>]+", re.I)
    email_pattern = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}")
    username_pattern = re.compile(r"(?i)(?:username|user|handle)[:=]\s*([a-z0-9_.-]{3,})")
    seen = set()
    for match in url_pattern.findall(text):
        value = match.rstrip(".,;)")
        key = ("url", value)
        if key not in seen:
            seen.add(key)
            findings.append({"type": "url", "value": value, "source": connector_name, "confidence": 0.75})
    for match in email_pattern.findall(text):
        key = ("email", match)
        if key not in seen:
            seen.add(key)
            findings.append({"type": "email", "value": match, "source": connector_name, "confidence": 0.7})
    for match in username_pattern.findall(text):
        key = ("username", match)
        if key not in seen:
            seen.add(key)
            findings.append({"type": "username", "value": match, "source": connector_name, "confidence": 0.55})
    return findings
