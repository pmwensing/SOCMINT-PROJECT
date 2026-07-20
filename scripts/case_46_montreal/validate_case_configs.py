#!/usr/bin/env python3
"""Validate the 46 Montreal operator configuration pack.

This is a lightweight text-level validator that intentionally avoids third-party
YAML dependencies. It verifies that the case, evidence-repo, search-pack, and
public-discovery config files contain the required scope controls and manifest
references.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONFIG_FILES = {
    "case": ROOT / "config" / "cases" / "46_montreal.case.yaml",
    "evidence_repo": ROOT / "config" / "evidence_repos" / "46_montreal_evidence_repo.yaml",
    "search_pack": ROOT / "config" / "search_packs" / "46_montreal_keywords.yaml",
    "public_sources": ROOT / "config" / "crawlers" / "46_montreal_public_sources.yaml",
}

REQUIRED_CASE_MARKERS = [
    "case_46_montreal",
    "46 Montreal Street",
    "46MONST",
    "directly involved",
    "559 Macdonnel",
    "71 Cowdy",
    "Cowdy Street",
    "candidate_entities_require_review: true",
    "no_unscoped_export: true",
]

REQUIRED_EVIDENCE_REPO_MARKERS = [
    "pmwensing/46-montreal-evidence-private",
    "manifest_index_review_export_layer",
    "original_file_storage_by_default: false",
    "Google Drive",
    "OneDrive",
    "TeraBox",
    "hash_required: true",
    "chain_of_custody_required: true",
    "EVIDENCE_REGISTER.csv",
    "EVIDENCE_LOCATION_MAP.csv",
    "BACKUP_VERIFICATION_LOG.csv",
]

REQUIRED_SEARCH_PACK_MARKERS = [
    "46_montreal_entity_aware_search_pack",
    "46 Montreal Street",
    "CEBD202505980-1",
    "240821-000468",
    "entity_query_templates",
    "negative_filters",
    "unrelated_entity_searches_blocked: true",
]

REQUIRED_PUBLIC_SOURCE_MARKERS = [
    "Public Record and Deep-Index Discovery Layer",
    "allowed_scope_only: true",
    "direct_entity_relevance_required: true",
    "robots_check_required: true",
    "terms_review_required: true",
    "public_access_required: true",
    "source_allowlist_required: true",
    "no_unrelated_entity_expansion: true",
    "human_review_required_before_dossier: true",
]

CHECKS = {
    "case": REQUIRED_CASE_MARKERS,
    "evidence_repo": REQUIRED_EVIDENCE_REPO_MARKERS,
    "search_pack": REQUIRED_SEARCH_PACK_MARKERS,
    "public_sources": REQUIRED_PUBLIC_SOURCE_MARKERS,
}


@dataclass(frozen=True)
class Finding:
    check: str
    status: str
    detail: str


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def validate_required_markers(name: str, path: Path, markers: list[str]) -> list[Finding]:
    text = read_text(path)
    findings: list[Finding] = []

    if not path.exists():
        return [Finding(name, "fail", f"Missing file: {path}")]

    findings.append(Finding(f"{name}.exists", "pass", str(path)))
    for marker in markers:
        status = "pass" if marker in text else "fail"
        findings.append(
            Finding(
                f"{name}.marker",
                status,
                f"Required marker {'found' if status == 'pass' else 'missing'}: {marker}",
            )
        )
    return findings


def validate_cross_file_controls() -> list[Finding]:
    case_text = read_text(CONFIG_FILES["case"])
    crawler_text = read_text(CONFIG_FILES["public_sources"])
    search_text = read_text(CONFIG_FILES["search_pack"])

    findings: list[Finding] = []

    cowdy_in_case_exclusions = all(
        term in case_text for term in ["71 Cowdy", "81 Cowdy", "Cowdy Street"]
    )
    findings.append(
        Finding(
            "cross.cowdy_exclusions",
            "pass" if cowdy_in_case_exclusions else "fail",
            "Cowdy address exclusions present in case config.",
        )
    )

    macdonnel_limited = "559 Macdonnel" in case_text and "mitigation" in case_text
    findings.append(
        Finding(
            "cross.mitigation_context",
            "pass" if macdonnel_limited else "fail",
            "559 Macdonnel is present as relocation / mitigation context.",
        )
    )

    entity_scope_gate = (
        "direct_entity_relevance_required: true" in crawler_text
        and "unrelated_entity_searches_blocked: true" in search_text
    )
    findings.append(
        Finding(
            "cross.entity_scope_gate",
            "pass" if entity_scope_gate else "fail",
            "Entity search/crawl expansion requires direct 46 Montreal relevance.",
        )
    )

    return findings


def main() -> int:
    findings: list[Finding] = []
    for name, path in CONFIG_FILES.items():
        findings.extend(validate_required_markers(name, path, CHECKS[name]))
    findings.extend(validate_cross_file_controls())

    status = "pass"
    if any(item.status == "fail" for item in findings):
        status = "fail"

    report = {
        "schema": "socmint.case_46_montreal.config_validation.v1",
        "status": status,
        "finding_count": len(findings),
        "findings": [asdict(item) for item in findings],
    }
    print(json.dumps(report, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
