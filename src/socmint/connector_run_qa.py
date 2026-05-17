from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .connector_normalizers import NORMALIZER_SCHEMA, normalize_connector_output
from .connector_runtime import connector_runtime_health

CONNECTOR_RUN_QA_SCHEMA = "socmint.connector_run_qa.v11_8"

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
            "stdout": json.dumps({
                "GitHub": {"status": "found", "url": "https://github.com/example_user_001"},
                "GitLab": {"exists": True, "profile_url": "https://gitlab.com/example_user_001"},
            }),
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
    samples = [_sample_result(connector, sample) for connector, sample in SAMPLE_RESULTS.items()]
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


def runtime_ready_report() -> dict[str, Any]:
    runtime = connector_runtime_health()
    ready = {item["name"] for item in runtime.get("connectors", []) if item.get("status") == "ready"}
    core = {"maigret", "sherlock", "socialscan", "holehe", "h8mail"}
    missing_core = sorted(core - ready)
    optional_missing = sorted({"phoneinfoga", "archivebox"} - ready)
    return {
        "schema": CONNECTOR_RUN_QA_SCHEMA,
        "status": "pass" if not missing_core else "needs_connector_build",
        "runtime_schema": runtime.get("schema"),
        "summary": runtime.get("summary", {}),
        "ready_core_connectors": sorted(core.intersection(ready)),
        "missing_core_connectors": missing_core,
        "optional_missing_connectors": optional_missing,
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
                issue for issue, passed in {
                    "normalization_samples": normalization["status"] == "pass",
                    "core_connector_runtime": runtime["status"] == "pass",
                }.items() if not passed
            ],
        },
    }
