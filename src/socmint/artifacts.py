import hashlib
import json
import os
from pathlib import Path


DEFAULT_ARTIFACT_ROOT = "var/socmint/artifacts"


def artifact_root() -> Path:
    root = Path(os.environ.get("SOCMINT_ARTIFACT_DIR", DEFAULT_ARTIFACT_ROOT))
    root.mkdir(parents=True, exist_ok=True)
    return root


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json_artifact(kind: str, payload: dict, prefix: str = "artifact") -> dict:
    data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    digest = sha256_bytes(data)
    directory = artifact_root() / kind
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{prefix}-{digest[:16]}.json"
    path.write_bytes(data)
    return {
        "kind": kind,
        "path": str(path),
        "sha256": digest,
        "mime_type": "application/json",
        "size_bytes": len(data),
    }
