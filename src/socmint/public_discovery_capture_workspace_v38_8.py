from __future__ import annotations

from typing import Any

from .browsertrix_production_enablement_v38_6_4 import current_enablements
from .evidence_ingestion_v29_4 import current_artifacts
from .execution_reconciliation_read_v35_4 import list_uncertain_executions
from .operational_import_v37_1 import current_imports
from .passive_archive_discovery_v38_3 import current_passive_batches
from .public_capture_triage_v38_7 import current_triage_records
from .public_discovery_policy_gate_v38_2 import current_gate_decisions
from .public_discovery_request_v38_1 import current_discovery_requests
from .source_independence_v36_4 import current_independence_assessments
from .source_registry_v36_1 import current_sources
from .synthetic_capture_provenance_v38_4 import current_synthetic_captures

SCHEMA = "socmint.public_discovery_capture_workspace.v38_8"
VERSION = "v38.8.0"


def _required(value: Any) -> str:
    return str(value or "").strip()


def _hash_prefix(value: Any) -> str | None:
    raw = _required(value)
    return raw[:16] if raw else None


def _request_projection(item: dict[str, Any]) -> dict[str, Any]:
    manifest = item.get("manifest") or {}
    limits = manifest.get("resource_limits") or {}
    return {
        "discovery_request_id": item.get("discovery_request_id"),
        "recorded_at": item.get("recorded_at"),
        "case_id": manifest.get("case_id"),
        "source_class": manifest.get("source_class"),
        "adapter_intent": manifest.get("adapter_intent"),
        "jurisdiction": manifest.get("jurisdiction"),
        "query_count": len(manifest.get("query_terms") or []),
        "seed_url_count": len(manifest.get("seed_urls") or []),
        "approved_domains": list(limits.get("allowed_domains") or []),
        "max_pages": limits.get("max_pages"),
        "max_depth": limits.get("max_depth"),
        "execution_eligible": item.get("execution_eligible") is True,
    }


def _gate_projection(item: dict[str, Any]) -> dict[str, Any]:
    evaluation = item.get("evaluation") or {}
    return {
        "gate_decision_id": item.get("gate_decision_id"),
        "discovery_request_id": item.get("discovery_request_id"),
        "recorded_at": item.get("recorded_at"),
        "decision": item.get("decision"),
        "source_tier": evaluation.get("source_tier"),
        "direct_case_relevance": evaluation.get("direct_case_relevance") is True,
        "candidate_entity_reviewed": evaluation.get("candidate_entity_reviewed")
        is True,
        "public_access_confirmed": evaluation.get("public_access_confirmed") is True,
        "robots_decision": evaluation.get("robots_decision"),
        "terms_decision": evaluation.get("terms_decision"),
        "decision_blockers": list(item.get("decision_blockers") or []),
        "passive_discovery_eligible": item.get("passive_discovery_eligible") is True,
        "live_network_eligible": item.get("live_network_eligible") is True,
    }


def _passive_projection(item: dict[str, Any]) -> dict[str, Any]:
    candidates = list(item.get("candidates") or [])
    counts = item.get("record_counts") or item.get("counts") or {}
    return {
        "passive_discovery_batch_id": item.get("passive_discovery_batch_id"),
        "gate_decision_id": item.get("gate_decision_id"),
        "provider": item.get("provider"),
        "recorded_at": item.get("recorded_at"),
        "candidate_count": len(candidates),
        "accepted_count": int(counts.get("accepted") or 0),
        "duplicate_count": int(counts.get("duplicate") or 0),
        "quarantined_count": int(counts.get("quarantined") or 0),
        "network_request_performed": item.get("network_request_performed") is True,
        "review_required": any(
            candidate.get("review_required") is True for candidate in candidates
        ),
    }


def _synthetic_projection(item: dict[str, Any]) -> dict[str, Any]:
    manifest = item.get("capture_manifest") or item.get("manifest") or {}
    finalization = item.get("finalization") or {}
    return {
        "synthetic_capture_id": item.get("synthetic_capture_id"),
        "recorded_at": item.get("recorded_at"),
        "case_id": item.get("case_id") or manifest.get("case_id"),
        "provenance_status": item.get("provenance_status"),
        "file_count": len(item.get("capture_files") or manifest.get("files") or []),
        "artifact_binding_count": len(
            finalization.get("artifact_bindings")
            or item.get("artifact_bindings")
            or []
        ),
        "source_registered": bool(
            finalization.get("source_binding") or finalization.get("source_id")
        ),
        "import_registered": bool(
            finalization.get("import_binding")
            or finalization.get("operational_import_id")
        ),
        "network_request_performed": item.get("network_request_performed") is True,
    }


def _artifact_projection(item: dict[str, Any]) -> dict[str, Any]:
    binding = item.get("contract_binding") or {}
    acquisition = item.get("acquisition") or {}
    return {
        "artifact_id": item.get("artifact_id"),
        "artifact_state": item.get("artifact_state"),
        "case_id": binding.get("case_id"),
        "content_sha256_prefix": _hash_prefix(item.get("content_sha256")),
        "content_type": acquisition.get("content_type"),
        "byte_size": acquisition.get("byte_size"),
        "duplicate_of_artifact_id": item.get("duplicate_of_artifact_id"),
        "observation_count": int(item.get("observation_count") or 0),
        "recorded_at": item.get("recorded_at"),
    }


def _source_projection(item: dict[str, Any]) -> dict[str, Any]:
    capture = item.get("capture") or {}
    return {
        "source_id": item.get("source_id"),
        "case_id": item.get("case_id"),
        "source_type": item.get("source_type"),
        "publisher_or_operator": item.get("publisher_or_operator"),
        "original_or_derived": item.get("original_or_derived"),
        "canonical_url": capture.get("canonical_url"),
        "captured_at": capture.get("captured_at"),
        "content_sha256_prefix": _hash_prefix(capture.get("content_sha256")),
        "capture_artifact_id": capture.get("capture_artifact_id"),
        "capture_integrity_verified": item.get("capture_integrity_verified") is True,
        "independence_assessed": item.get("independence_assessed") is True,
        "reliability_assessed": item.get("reliability_assessed") is True,
    }


def _independence_projection(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "independence_group_id": item.get("independence_group_id"),
        "case_id": item.get("case_id"),
        "relationship": item.get("relationship"),
        "independence_score": item.get("independence_score"),
        "source_count": len(item.get("source_ids") or []),
        "limitation_count": len(item.get("limitations") or []),
        "recorded_at": item.get("recorded_at"),
    }


def _import_projection(item: dict[str, Any]) -> dict[str, Any]:
    envelope = item.get("envelope") or {}
    counts = item.get("record_counts") or {}
    return {
        "operational_import_id": item.get("operational_import_id"),
        "case_id": envelope.get("case_id"),
        "purpose": envelope.get("purpose"),
        "export_format": envelope.get("export_format"),
        "declared_record_count": envelope.get("declared_record_count"),
        "staged_count": int(counts.get("staged") or 0),
        "accepted_count": int(counts.get("accepted") or 0),
        "quarantined_count": int(counts.get("quarantined") or 0),
        "duplicate_count": int(counts.get("duplicate") or 0),
        "recorded_at": item.get("recorded_at"),
    }


def _enablement_projection(item: dict[str, Any]) -> dict[str, Any]:
    definition = item.get("definition") or {}
    scope = definition.get("authorized_scope") or {}
    return {
        "production_enablement_id": item.get("production_enablement_id"),
        "enablement_state": item.get("enablement_state"),
        "deployment_id": scope.get("deployment_id") or definition.get("deployment_id"),
        "case_id": scope.get("case_id"),
        "approved_domain": scope.get("approved_domain"),
        "valid_from": definition.get("valid_from"),
        "expires_at": definition.get("expires_at"),
        "single_use": definition.get("single_use") is True,
        "automatic_execution": definition.get("automatic_execution") is True,
        "automatic_retry": definition.get("automatic_retry") is True,
        "recorded_at": item.get("recorded_at"),
    }


def _triage_projection(item: dict[str, Any]) -> dict[str, Any]:
    source_triage = list(item.get("source_triage") or [])
    classifications: dict[str, int] = {}
    for entry in source_triage:
        classification = _required((entry.get("relevance") or {}).get("classification"))
        if classification:
            classifications[classification] = classifications.get(classification, 0) + 1
    return {
        "capture_triage_id": item.get("capture_triage_id"),
        "case_id": item.get("case_id"),
        "recorded_at": item.get("recorded_at"),
        "counts": dict(item.get("counts") or {}),
        "relevance_classifications": dict(sorted(classifications.items())),
        "unconfirmed_mirror_proposal_count": len(item.get("mirror_proposals") or []),
        "change_summary_count": len(item.get("change_summaries") or []),
        "factual_significance_assigned": any(
            entry.get("factual_significance_assigned") is True
            for entry in item.get("change_summaries") or []
        ),
        "causation_assigned": any(
            entry.get("causation_assigned") is True
            for entry in item.get("change_summaries") or []
        ),
    }


def _uncertain_projection(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_id": item.get("execution_id"),
        "case_id": item.get("case_id"),
        "governance_action": item.get("governance_action"),
        "state": item.get("state"),
        "state_version": item.get("state_version"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "ledger_consistent": item.get("ledger_consistent") is True,
        "result_envelope_exists": item.get("result_envelope_exists") is True,
        "automatic_retry": item.get("automatic_retry") is True,
        "delegate_invocation_available": item.get("delegate_invocation_available")
        is True,
    }


def _finding(
    key: str,
    count: int,
    message: str,
    next_action: str,
    severity: str = "review",
) -> dict[str, Any]:
    return {
        "key": key,
        "count": count,
        "severity": severity,
        "message": message,
        "next_action": next_action,
    }


def build_public_discovery_capture_workspace() -> dict[str, Any]:
    requests = [_request_projection(item) for item in current_discovery_requests()]
    gates = [_gate_projection(item) for item in current_gate_decisions()]
    passive_batches = [_passive_projection(item) for item in current_passive_batches()]
    synthetic_captures = [
        _synthetic_projection(item) for item in current_synthetic_captures()
    ]
    artifacts = [_artifact_projection(item) for item in current_artifacts()]
    sources = [_source_projection(item) for item in current_sources()]
    independence = [
        _independence_projection(item) for item in current_independence_assessments()
    ]
    imports = [_import_projection(item) for item in current_imports()]
    enablements = [_enablement_projection(item) for item in current_enablements()]
    triage = [_triage_projection(item) for item in current_triage_records()]
    uncertain_payload = list_uncertain_executions(limit=100, offset=0)
    uncertain = [
        _uncertain_projection(item)
        for item in uncertain_payload.get("executions") or []
    ]

    blocked_gate_count = sum(item.get("decision") == "block" for item in gates)
    quarantined_passive_count = sum(
        int(item.get("quarantined_count") or 0) for item in passive_batches
    )
    incomplete_synthetic_count = sum(
        item.get("provenance_status") != "complete" for item in synthetic_captures
    )
    candidate_review_count = sum(
        int((item.get("counts") or {}).get("candidate_review") or 0)
        for item in triage
    )
    out_of_scope_count = sum(
        int((item.get("counts") or {}).get("out_of_scope") or 0) for item in triage
    )
    unresolved_mirror_count = sum(
        int(item.get("unconfirmed_mirror_proposal_count") or 0) for item in triage
    )
    active_enablement_count = sum(
        item.get("enablement_state") in {"active", "claimed"}
        for item in enablements
    )
    accepted_artifact_count = sum(
        item.get("artifact_state") == "accepted" for item in artifacts
    )
    support_eligible_count = sum(
        int((item.get("counts") or {}).get("support_eligible") or 0)
        for item in triage
    )

    findings: list[dict[str, Any]] = []
    if blocked_gate_count:
        findings.append(
            _finding(
                "blocked_discovery_gate",
                blocked_gate_count,
                "One or more public-discovery requests are blocked by the recorded policy gate.",
                "Review the immutable blocker list; do not execute blocked requests.",
                "block",
            )
        )
    if quarantined_passive_count:
        findings.append(
            _finding(
                "quarantined_passive_candidate",
                quarantined_passive_count,
                "Passive archive candidates require quarantine review.",
                "Review malformed or incomplete candidate metadata before any capture decision.",
            )
        )
    if incomplete_synthetic_count:
        findings.append(
            _finding(
                "synthetic_provenance_incomplete",
                incomplete_synthetic_count,
                "Synthetic capture provenance has not completed its separate artifact/source/import gates.",
                "Complete the v29 acceptance and v36/v37 bindings without automatic promotion.",
            )
        )
    if candidate_review_count:
        findings.append(
            _finding(
                "capture_candidate_review_pending",
                candidate_review_count,
                "Capture relevance remains candidate-review-only.",
                "Complete a separate analyst relevance review before support or handoff use.",
            )
        )
    if out_of_scope_count:
        findings.append(
            _finding(
                "out_of_scope_capture",
                out_of_scope_count,
                "Captures are explicitly classified out of scope.",
                "Keep them excluded from support, handoff, observation, and dossier workflows.",
                "info",
            )
        )
    if unresolved_mirror_count:
        findings.append(
            _finding(
                "mirror_proposal_unconfirmed",
                unresolved_mirror_count,
                "Exact-hash mirror proposals have not been confirmed through v36.4.",
                "Confirm or reject each proposal separately; do not count copies as corroboration.",
            )
        )
    if active_enablement_count:
        findings.append(
            _finding(
                "browsertrix_enablement_active",
                active_enablement_count,
                "A time-bounded Browsertrix production enablement is active or claimed.",
                "Verify expiry, revocation status, and single-use execution state before any operator action.",
                "high",
            )
        )
    if uncertain:
        findings.append(
            _finding(
                "execution_outcome_uncertain",
                len(uncertain),
                "Durable executions have uncertain external outcomes and cannot be replayed automatically.",
                "Use the existing read-only reconciliation and recovery workflow.",
                "high",
            )
        )

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": "ready",
        "read_only": True,
        "summary": {
            "discovery_request_count": len(requests),
            "allowing_gate_count": sum(
                item.get("decision") == "allow" for item in gates
            ),
            "blocked_gate_count": blocked_gate_count,
            "passive_batch_count": len(passive_batches),
            "passive_candidate_count": sum(
                int(item.get("candidate_count") or 0) for item in passive_batches
            ),
            "synthetic_capture_count": len(synthetic_captures),
            "completed_synthetic_capture_count": sum(
                item.get("provenance_status") == "complete"
                for item in synthetic_captures
            ),
            "artifact_count": len(artifacts),
            "accepted_artifact_count": accepted_artifact_count,
            "source_count": len(sources),
            "independence_group_count": len(independence),
            "operational_import_count": len(imports),
            "production_enablement_count": len(enablements),
            "active_or_claimed_enablement_count": active_enablement_count,
            "capture_triage_count": len(triage),
            "support_eligible_capture_count": support_eligible_count,
            "uncertain_execution_count": len(uncertain),
            "finding_count": len(findings),
        },
        "findings": findings,
        "capability_inventory": [
            {
                "slice": "v38.1",
                "capability": "discovery request and crawl manifest",
                "execution_mode": "registration_only",
            },
            {
                "slice": "v38.2",
                "capability": "source, scope, robots, terms and resource gate",
                "execution_mode": "immutable_allow_or_block",
            },
            {
                "slice": "v38.3",
                "capability": "passive archive candidate normalization",
                "execution_mode": "offline_candidates",
            },
            {
                "slice": "v38.4",
                "capability": "synthetic capture provenance",
                "execution_mode": "offline_two_phase",
            },
            {
                "slice": "v38.5",
                "capability": "official public HTTP capture",
                "execution_mode": "operator_confirmed_live_network",
            },
            {
                "slice": "v38.6",
                "capability": "Browsertrix preservation request and validation",
                "execution_mode": "operator_confirmed",
            },
            {
                "slice": "v38.6.3",
                "capability": "deployment certification",
                "execution_mode": "fictional_test_fixture_only",
            },
            {
                "slice": "v38.6.4",
                "capability": "production enablement",
                "execution_mode": "certification_bound_single_use",
            },
            {
                "slice": "v38.7",
                "capability": "duplicate, change, relevance and handoff triage",
                "execution_mode": "explicit_analyst_review",
            },
        ],
        "discovery_request_inventory": requests,
        "gate_decision_inventory": gates,
        "passive_discovery_inventory": passive_batches,
        "synthetic_capture_inventory": synthetic_captures,
        "artifact_inventory": artifacts,
        "source_inventory": sources,
        "source_independence_inventory": independence,
        "operational_import_inventory": imports,
        "production_enablement_inventory": enablements,
        "capture_triage_inventory": triage,
        "uncertain_execution_inventory": uncertain,
        "controls": {
            "safe_projection_only": True,
            "raw_content_exposed": False,
            "credentials_exposed": False,
            "cookies_exposed": False,
            "authorization_headers_exposed": False,
            "confirmation_hashes_exposed": False,
            "private_storage_paths_exposed": False,
            "runtime_commands_exposed": False,
            "automatic_collection": False,
            "automatic_retry": False,
            "automatic_artifact_acceptance": False,
            "automatic_source_independence_assessment": False,
            "automatic_observation_promotion": False,
            "automatic_truth_assignment": False,
            "automatic_entity_merge": False,
            "automatic_claim_approval": False,
            "automatic_dossier_mutation": False,
            "automatic_import_staging": False,
            "automatic_export": False,
            "automatic_publication": False,
            "write_actions_exposed_by_workspace": [],
        },
    }
