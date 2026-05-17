from __future__ import annotations

import importlib
import pkgutil
import re
from pathlib import Path
from typing import Any

RUNTIME_IMPORT_HEALTH_SCHEMA = "socmint.runtime_import_health.v11_5"

ABSOLUTE_IMPORT_PATTERNS = (
    re.compile(r"^\s*import\s+socmint\b", re.MULTILINE),
    re.compile(r"^\s*from\s+socmint\b", re.MULTILINE),
)

IGNORED_IMPORT_PROBE_PREFIXES = (
    "src.socmint.tests",
)


def source_import_scan(root: str | Path = "src/socmint") -> dict[str, Any]:
    root_path = Path(root)
    hits: list[dict[str, Any]] = []
    if root_path.exists():
        for path in sorted(root_path.rglob("*.py")):
            text = path.read_text(errors="ignore")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if any(pattern.search(line) for pattern in ABSOLUTE_IMPORT_PATTERNS):
                    hits.append({"path": str(path), "line": line_number, "text": line.strip()})
    return {
        "schema": RUNTIME_IMPORT_HEALTH_SCHEMA,
        "status": "pass" if not hits else "needs_cleanup",
        "hit_count": len(hits),
        "hits": hits,
    }


def package_import_probe() -> dict[str, Any]:
    import src.socmint as package

    checked = 0
    failures: list[dict[str, str]] = []
    prefix = package.__name__ + "."
    for module in pkgutil.walk_packages(package.__path__, prefix):
        name = module.name
        if any(name.startswith(ignore) for ignore in IGNORED_IMPORT_PROBE_PREFIXES):
            continue
        checked += 1
        try:
            importlib.import_module(name)
        except Exception as exc:
            message = str(exc)
            if "No module named 'socmint'" in message or 'No module named "socmint"' in message:
                failures.append({"module": name, "type": type(exc).__name__, "error": message})
    return {
        "schema": RUNTIME_IMPORT_HEALTH_SCHEMA,
        "status": "pass" if not failures else "fail",
        "checked_modules": checked,
        "failure_count": len(failures),
        "failures": failures,
    }


def runtime_import_health_report(root: str | Path = "src/socmint") -> dict[str, Any]:
    source_scan = source_import_scan(root)
    package_probe = package_import_probe()
    return {
        "schema": RUNTIME_IMPORT_HEALTH_SCHEMA,
        "status": "pass" if source_scan["status"] == "pass" and package_probe["status"] == "pass" else "fail",
        "source_scan": source_scan,
        "package_probe": package_probe,
    }
