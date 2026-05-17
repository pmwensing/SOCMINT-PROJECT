from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Any

RUNTIME_IMPORT_HEALTH_SCHEMA = "socmint.runtime_import_health.v11_5"
LEGACY_IMPORT_PATTERNS = ("import socmint", "from socmint")
CRITICAL_MODULES = (
    "src.socmint.wsgi",
    "src.socmint.dashboard",
    "src.socmint.command_center",
    "src.socmint.command_center_routes",
    "src.socmint.production_release_routes",
    "src.socmint.release_integrity",
    "src.socmint.product_registry",
)


def _is_source_path(path: Path) -> bool:
    parts = set(path.parts)
    if ".git" in parts or "venv" in parts or ".venv" in parts or "__pycache__" in parts:
        return False
    return path.suffix == ".py"


def legacy_absolute_import_scan(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root)
    findings: list[dict[str, Any]] = []
    for path in sorted(root_path.rglob("*.py")):
        if not _is_source_path(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not any(pattern in text for pattern in LEGACY_IMPORT_PATTERNS):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "socmint" or alias.name.startswith("socmint."):
                        findings.append({"path": str(path), "line": node.lineno, "import": f"import {alias.name}"})
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "socmint" or module.startswith("socmint."):
                    names = ", ".join(alias.name for alias in node.names)
                    findings.append({"path": str(path), "line": node.lineno, "import": f"from {module} import {names}"})
    runtime_source_findings = [item for item in findings if item["path"].startswith("src/socmint/")]
    return {
        "schema": RUNTIME_IMPORT_HEALTH_SCHEMA,
        "status": "pass" if not runtime_source_findings else "needs_review",
        "legacy_import_count": len(findings),
        "runtime_source_import_count": len(runtime_source_findings),
        "findings": findings,
        "runtime_source_findings": runtime_source_findings,
    }


def critical_module_import_report() -> dict[str, Any]:
    modules: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for module_name in CRITICAL_MODULES:
        try:
            importlib.import_module(module_name)
            modules.append({"module": module_name, "status": "pass"})
        except Exception as exc:
            item = {"module": module_name, "status": "fail", "error": f"{type(exc).__name__}: {exc}"}
            modules.append(item)
            failures.append(item)
    return {
        "schema": RUNTIME_IMPORT_HEALTH_SCHEMA,
        "status": "pass" if not failures else "fail",
        "modules": modules,
        "failures": failures,
    }


def runtime_import_health(root: str | Path = ".") -> dict[str, Any]:
    scan = legacy_absolute_import_scan(root=root)
    critical = critical_module_import_report()
    checks = {
        "critical_modules_import": critical["status"] == "pass",
        "runtime_source_absolute_imports_clean": scan["runtime_source_import_count"] == 0,
    }
    status = "pass" if all(checks.values()) else "needs_review"
    return {
        "schema": RUNTIME_IMPORT_HEALTH_SCHEMA,
        "status": status,
        "checks": checks,
        "critical": critical,
        "legacy_import_scan": scan,
        "summary": {
            "critical_failure_count": len(critical.get("failures") or []),
            "legacy_import_count": scan.get("legacy_import_count", 0),
            "runtime_source_import_count": scan.get("runtime_source_import_count", 0),
        },
    }
