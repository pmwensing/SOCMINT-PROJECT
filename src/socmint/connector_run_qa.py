from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from typing import Any

from .connector_normalizers import NORMALIZER_SCHEMA, normalize_connector_output

CONNECTOR_RUN_QA_SCHEMA = "socmint.connector_run_qa.v11_8"
CORE_CONNECTORS = {"maigret", "sherlock", "socialscan", "holehe", "h8mail"}
OPTIONAL_CONNECTORS = {"phoneinfoga", "archivebox"}

SAMPLE_RESULTS: dict[str, dict[str, Any]] = {
    "sherlock": {
        "seed_value": "example_user_001",
        "seed_type": "username",
        "raw_result": {
            "status": "completed",
            "returncode": 0,
            "stdout": "[*] Checking username example_user_001\n[+] GitHub: https://github.com/example_user_001\n[+] Reddit: https://www.reddit.com/user/example_user_001\n",
            "stderr": "",
        },
        "expected_types": {"profile_url"},
    },
    "maigret": {
        "seed_value": "example_user_001",
        "seed_type": "username",
        "raw_result": {
            "status": "completed",
            "returncode": 0,
            "stdout": json.dumps(
                {
                    "GitHub": {
                        "status": "found",
                        "url": "https://github.com/example_user_001",
                    },
                    "GitLab": {
                        "exists": True,
                        "profile_url": "https://gitlab.com/example_user_001",
                    },
                }
            ),
            "stderr": "",
        },
        "expected_types": {"profile_url"},
    },
    "socialscan": {
        "seed_value": "test.person@example.com",
        "seed_type": "email",
        "raw_result": {
            "status": "completed",
            "returncode": 0,
            "stdout": "Email: test.person@example.com\nGitHub: registered\nSpotify: exists\nTwitter: not found\n",
            "stderr": "",
        },
        "expected_types": {"account_presence"},
    },
    "holehe": {
        "seed_value": "test.person@example.com",
        "seed_type": "email",
        "raw_result": {
            "status": "completed",
            "returncode": 0,
            "stdout": "[+] twitter.com\n[+] spotify.com\n[-] github.com\n",
            "stderr": "",
        },
        "expected_types": {"account_presence"},
    },
}


def _sample_result(connector: str, sample: dict[str, Any]) -> dict[str, Any]:
    findings = normalize_connector_output(
        connector,
        sample["seed_value"],
        sample["seed_type"],
        sample["raw_result"],
    )
    types = {item.get("type") for item in findings}
    expected = set(sample.get("expected_types") or set())
    return {
        "connector": connector,
        "status": "pass" if findings and expected.intersection(types) else "fail",
        "finding_count": len(findings),
        "finding_types": sorted(item for item in types if item),
        "expected_types": sorted(expected),
        "findings": findings,
    }


def normalization_qa_report() -> dict[str, Any]:
    samples = [
        _sample_result(connector, sample)
        for connector, sample in SAMPLE_RESULTS.items()
    ]
    passed = sum(1 for item in samples if item["status"] == "pass")
    return {
        "schema": CONNECTOR_RUN_QA_SCHEMA,
        "normalizer_schema": NORMALIZER_SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if passed == len(samples) else "fail",
        "passed_samples": passed,
        "total_samples": len(samples),
        "samples": samples,
    }


def _quick_connector_presence() -> dict[str, str | None]:
    return {
        "maigret": "python" if shutil.which("python") else None,
        "sherlock": shutil.which("sherlock"),
        "socialscan": shutil.which("socialscan"),
        "holehe": shutil.which("holehe"),
        "h8mail": shutil.which("h8mail"),
        "phoneinfoga": shutil.which("phoneinfoga"),
        "archivebox": shutil.which("archivebox"),
    }


def runtime_ready_report() -> dict[str, Any]:
    executables = _quick_connector_presence()
    ready = {name for name, path in executables.items() if path}
    missing_core = sorted(CORE_CONNECTORS - ready)
    optional_missing = sorted(OPTIONAL_CONNECTORS - ready)
    return {
        "schema": CONNECTOR_RUN_QA_SCHEMA,
        "status": "pass" if not missing_core else "needs_connector_build",
        "runtime_schema": "socmint.connector_runtime.fast_presence.v11_8",
        "summary": {
            "ready": len(ready),
            "missing_core": len(missing_core),
            "optional_missing": len(optional_missing),
        },
        "ready_core_connectors": sorted(CORE_CONNECTORS.intersection(ready)),
        "missing_core_connectors": missing_core,
        "optional_missing_connectors": optional_missing,
        "executables": executables,
        "note": "Fast QA route uses shutil.which only so frontend audit does not block on version probes.",
    }


def connector_run_qa_report() -> dict[str, Any]:
    normalization = normalization_qa_report()
    runtime = runtime_ready_report()
    ok = normalization["status"] == "pass" and runtime["status"] == "pass"
    return {
        "schema": CONNECTOR_RUN_QA_SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "pass" if ok else "needs_review",
        "normalization": normalization,
        "runtime": runtime,
        "qa_gate": {
            "decision": "go" if ok else "hold",
            "required_before_real_runs": [
                issue
                for issue, passed in {
                    "normalization_samples": normalization["status"] == "pass",
                    "core_connector_runtime": runtime["status"] == "pass",
                }.items()
                if not passed
            ],
        },
    }
