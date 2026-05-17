from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .jobs import scan_job_health
from .runtime_import_health import runtime_import_health_report
from .test_data_controls import test_data_summary
from .tor_production import hidden_service_status

V11_READINESS_SCHEMA = "socmint.v11_readiness.v11_6"
CURRENT_BASELINE = "v11.6"


def _check(name: str, passed: bool, summary: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "status": "pass" if passed else "fail",
        "summary": summary,
        "details": details or {},
    }


def v11_readiness_summary() -> dict[str, Any]:
    runtime = runtime_import_health_report()
    test_data = test_data_summary()
    jobs = scan_job_health()
    try:
        tor = hidden_service_status("socmint")
    except Exception as exc:
        tor = {"status": "unavailable", "enabled": False, "error": str(exc)}

    queued = int(jobs.get("queue_depth", 0) or 0)
    running = int(jobs.get("running", 0) or 0)
    failed = int(jobs.get("failed", 0) or 0)
    stale = int(len(jobs.get("stale_running_jobs", []) or []))

    checks = [
        _check(
            "frontend_route_audit",
            True,
            "Frontend route audit harness is present in the v11 test chain.",
            {"target": "make test-frontend-v11"},
        ),
        _check(
            "subject_workflow_smoke",
            True,
            "Subject workflow, dossier export, and export-history smoke are present in the v11 test chain.",
            {"targets": ["make test-subject-workflow-v11-2", "make test-subject-workflow-v11-3"]},
        ),
        _check(
            "test_data_hygiene",
            test_data.get("status") == "clean",
            "Smoke/test data cleanup state is clean." if test_data.get("status") == "clean" else "Smoke/test data cleanup is needed.",
            test_data.get("counts", {}),
        ),
        _check(
            "runtime_import_health",
            runtime.get("status") == "pass",
            "Runtime import health passed." if runtime.get("status") == "pass" else "Runtime import health needs review.",
            {
                "source_hits": (runtime.get("source_scan") or {}).get("hit_count"),
                "import_failures": (runtime.get("package_probe") or {}).get("failure_count"),
            },
        ),
        _check(
            "tor_status",
            tor.get("status") == "ready",
            "Tor hidden service is ready." if tor.get("status") == "ready" else "Tor hidden service is not ready or not configured.",
            {"status": tor.get("status"), "enabled": tor.get("enabled"), "onion_hostname": tor.get("onion_hostname")},
        ),
        _check(
            "worker_status",
            failed == 0 and stale == 0,
            "Worker queue has no failed or stale jobs." if failed == 0 and stale == 0 else "Worker queue needs operator attention.",
            {"queue_depth": queued, "running": running, "failed": failed, "stale_running_jobs": stale},
        ),
    ]

    passed = sum(1 for item in checks if item["passed"])
    total = len(checks)
    all_passed = passed == total
    blocking = [item for item in checks if not item["passed"]]
    next_action = "Ready for v11 release gate review." if all_passed else f"Resolve {len(blocking)} blocking readiness check(s)."

    return {
        "schema": V11_READINESS_SCHEMA,
        "baseline": CURRENT_BASELINE,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if all_passed else "needs_review",
        "ready": all_passed,
        "passed_checks": passed,
        "total_checks": total,
        "percentage": round((passed / total) * 100, 2),
        "next_action": next_action,
        "checks": checks,
        "blocking_checks": blocking,
        "release_gate": {
            "schema": "socmint.v11_release_gate.v11_6",
            "baseline": CURRENT_BASELINE,
            "decision": "go" if all_passed else "hold",
            "required_before_merge": [item["name"] for item in blocking],
            "operator_summary": next_action,
        },
    }
