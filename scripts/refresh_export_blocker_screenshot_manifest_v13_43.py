from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_MANIFEST = ROOT / "release" / "V13_42_EXPORT_BLOCKER_SCREENSHOT_ARTIFACT_MANIFEST.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def refresh_manifest(manifest_path: str | Path = DEFAULT_MANIFEST, root: str | Path = ROOT) -> dict[str, Any]:
    path = Path(manifest_path)
    root_path = Path(root)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["schema"] = "socmint.release_artifact_manifest.v13_43"
    manifest["version"] = "v13.43"
    manifest["refresh_script"] = "scripts/refresh_export_blocker_screenshot_manifest_v13_43.py"

    for item in manifest.get("artifacts", []):
        artifact_path = root_path / item["path"]
        item["exists"] = artifact_path.exists()
        if artifact_path.exists():
            item["size_bytes"] = artifact_path.stat().st_size
            item["sha256"] = sha256_file(artifact_path)
        else:
            item["size_bytes"] = 0
            item["sha256"] = None

    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    manifest = refresh_manifest()
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
