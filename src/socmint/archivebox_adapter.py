import json
import os
import shutil
import subprocess
from datetime import datetime, UTC
from pathlib import Path

from .artifacts import write_json_artifact


def archivebox_available() -> bool:
    return shutil.which("archivebox") is not None


def archivebox_data_dir() -> str | None:
    return os.environ.get("SOCMINT_ARCHIVEBOX_DIR") or os.environ.get(
        "ARCHIVEBOX_DATA_DIR"
    )


def archivebox_enabled() -> bool:
    value = os.environ.get("SOCMINT_ARCHIVEBOX_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def capture_url(url: str, timeout: int = 180) -> dict:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("ArchiveBox capture requires an HTTP/HTTPS URL.")

    if not archivebox_enabled():
        return dry_run_archivebox(url, "SOCMINT_ARCHIVEBOX_ENABLED is not enabled.")

    if not archivebox_available():
        return dry_run_archivebox(url, "archivebox executable is not installed.")

    data_dir = archivebox_data_dir()
    command = ["archivebox", "add", "--json", url]
    env = os.environ.copy()

    cwd = None
    if data_dir:
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        cwd = data_dir

    started_at = datetime.now(UTC).isoformat()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        payload = {
            "connector": "archivebox",
            "status": "timeout",
            "url": url,
            "command": command,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "ArchiveBox capture timed out.",
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
            "findings": [],
        }
        artifact = write_json_artifact("archivebox", payload, "archivebox-timeout")
        payload["artifact"] = artifact
        return payload

    payload = {
        "connector": "archivebox",
        "status": "completed" if result.returncode == 0 else "failed",
        "url": url,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
    }

    snapshot_refs = parse_archivebox_output(result.stdout)
    payload["snapshots"] = snapshot_refs
    payload["findings"] = [
        {
            "type": "archive_snapshot",
            "value": item.get("url") or url,
            "source": "archivebox",
            "confidence": 0.86,
            "context": item,
        }
        for item in snapshot_refs
    ]

    if not payload["findings"]:
        payload["findings"] = [
            {
                "type": "archive_candidate",
                "value": url,
                "source": "archivebox",
                "confidence": 0.72 if result.returncode == 0 else 0.45,
                "context": {
                    "returncode": result.returncode,
                    "stderr": result.stderr,
                },
            }
        ]

    artifact = write_json_artifact("archivebox", payload, "archivebox-capture")
    payload["artifact"] = artifact
    return payload


def parse_archivebox_output(stdout: str) -> list[dict]:
    text = stdout or ""
    snapshots = []

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        candidates = data.get("output") or data.get("results") or data.get("snapshots")
        if isinstance(candidates, list):
            for item in candidates:
                if isinstance(item, dict):
                    snapshots.append(normalize_snapshot(item))
        elif data.get("url") or data.get("timestamp"):
            snapshots.append(normalize_snapshot(data))

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                snapshots.append(normalize_snapshot(item))

    return [item for item in snapshots if item.get("url") or item.get("timestamp")]


def normalize_snapshot(item: dict) -> dict:
    return {
        "url": item.get("url") or item.get("bookmarked_url"),
        "timestamp": item.get("timestamp"),
        "title": item.get("title"),
        "index_path": item.get("index_path") or item.get("path"),
        "archive_path": item.get("archive_path"),
        "status": item.get("status"),
    }


def dry_run_archivebox(url: str, reason: str) -> dict:
    payload = {
        "connector": "archivebox",
        "status": "dry_run",
        "url": url,
        "reason": reason,
        "findings": [
            {
                "type": "archive_candidate",
                "value": url,
                "source": "archivebox",
                "confidence": 0.82,
                "context": {"reason": reason},
            }
        ],
        "created_at": datetime.now(UTC).isoformat(),
    }
    artifact = write_json_artifact("archivebox", payload, "archivebox-dry-run")
    payload["artifact"] = artifact
    return payload
