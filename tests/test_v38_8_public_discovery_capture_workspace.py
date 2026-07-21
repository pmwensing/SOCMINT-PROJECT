from src.socmint import public_discovery_capture_workspace_v38_8 as workspace


def _patch_empty(monkeypatch):
    for name in (
        "current_discovery_requests",
        "current_gate_decisions",
        "current_passive_batches",
        "current_synthetic_captures",
        "current_artifacts",
        "current_sources",
        "current_independence_assessments",
        "current_imports",
        "current_enablements",
        "current_triage_records",
    ):
        monkeypatch.setattr(workspace, name, lambda: [])
    monkeypatch.setattr(
        workspace,
        "list_uncertain_executions",
        lambda limit, offset: {"executions": []},
    )


def _patch_populated(monkeypatch):
    _patch_empty(monkeypatch)
    monkeypatch.setattr(
        workspace,
        "current_discovery_requests",
        lambda: [
            {
                "discovery_request_id": "request-a",
                "recorded_at": "2026-07-21T01:00:00Z",
                "execution_eligible": False,
                "manifest": {
                    "case_id": "case-a",
                    "source_class": "official_public_source",
                    "adapter_intent": "public_http",
                    "jurisdiction": "Ontario",
                    "query_terms": ["fictional order"],
                    "seed_urls": ["https://records.example.test/"],
                    "resource_limits": {
                        "allowed_domains": ["records.example.test"],
                        "max_pages": 2,
                        "max_depth": 1,
                    },
                },
                "authorization_binding": {"secret": "must-not-leak"},
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_gate_decisions",
        lambda: [
            {
                "gate_decision_id": "gate-a",
                "discovery_request_id": "request-a",
                "recorded_at": "2026-07-21T01:01:00Z",
                "decision": "block",
                "decision_blockers": ["robots_allow_required"],
                "passive_discovery_eligible": False,
                "live_network_eligible": False,
                "evaluation": {
                    "source_tier": "official",
                    "direct_case_relevance": True,
                    "candidate_entity_reviewed": False,
                    "public_access_confirmed": True,
                    "robots_decision": "block",
                    "terms_decision": "reviewed_allow",
                },
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_passive_batches",
        lambda: [
            {
                "passive_discovery_batch_id": "batch-a",
                "gate_decision_id": "gate-a",
                "provider": "common_crawl",
                "recorded_at": "2026-07-21T01:02:00Z",
                "candidates": [{"review_required": True}],
                "record_counts": {"accepted": 0, "duplicate": 0, "quarantined": 1},
                "raw_response": "must-not-leak",
                "network_request_performed": False,
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_synthetic_captures",
        lambda: [
            {
                "synthetic_capture_id": "synthetic-a",
                "case_id": "case-a",
                "recorded_at": "2026-07-21T01:03:00Z",
                "provenance_status": "artifacts_prepared",
                "capture_files": [{"role": "primary_html"}],
                "raw_content": "must-not-leak",
                "network_request_performed": False,
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_artifacts",
        lambda: [
            {
                "artifact_id": "artifact-a",
                "artifact_state": "accepted",
                "content_sha256": "a" * 64,
                "contract_binding": {
                    "case_id": "case-a",
                    "authorization_binding": {"secret": "must-not-leak"},
                },
                "acquisition": {
                    "content_type": "text/html",
                    "byte_size": 100,
                    "provenance_metadata": {"private_path": "/secret"},
                },
                "observation_count": 0,
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_sources",
        lambda: [
            {
                "source_id": "source-a",
                "case_id": "case-a",
                "source_type": "official_record",
                "publisher_or_operator": "Fictional Authority",
                "original_or_derived": "original",
                "capture_integrity_verified": True,
                "independence_assessed": False,
                "reliability_assessed": False,
                "capture": {
                    "canonical_url": "https://records.example.test/notice",
                    "captured_at": "2026-07-21T01:04:00Z",
                    "content_sha256": "a" * 64,
                    "capture_artifact_id": "artifact-a",
                    "authorization_reference": "must-not-leak",
                },
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_independence_assessments",
        lambda: [
            {
                "independence_group_id": "group-a",
                "case_id": "case-a",
                "relationship": "mirror",
                "independence_score": 0,
                "source_ids": ["source-a", "source-b"],
                "limitations": ["fictional limitation"],
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_imports",
        lambda: [
            {
                "operational_import_id": "import-a",
                "envelope": {
                    "case_id": "case-a",
                    "purpose": "Review fictional public capture.",
                    "export_format": "html",
                    "declared_record_count": 1,
                    "collection_context": {"raw": "must-not-leak"},
                },
                "record_counts": {},
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_enablements",
        lambda: [
            {
                "production_enablement_id": "enablement-a",
                "enablement_state": "claimed",
                "definition": {
                    "valid_from": "2026-07-21T01:00:00Z",
                    "expires_at": "2026-07-21T02:00:00Z",
                    "single_use": True,
                    "automatic_execution": False,
                    "automatic_retry": False,
                    "certification_binding": {"hash": "must-not-leak"},
                    "authorized_scope": {
                        "deployment_id": "deployment-a",
                        "case_id": "case-a",
                        "approved_domain": "records.example.test",
                        "image_digest": "must-not-leak",
                        "network_name": "must-not-leak",
                        "approved_storage_root": "/must-not-leak",
                    },
                },
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "current_triage_records",
        lambda: [
            {
                "capture_triage_id": "triage-a",
                "case_id": "case-a",
                "counts": {
                    "support_eligible": 1,
                    "candidate_review": 1,
                    "out_of_scope": 1,
                },
                "source_triage": [
                    {"relevance": {"classification": "direct_case"}},
                    {"relevance": {"classification": "candidate_review"}},
                ],
                "mirror_proposals": [{"mirror_proposal_id": "proposal-a"}],
                "change_summaries": [
                    {
                        "change_state": "content_hash_changed",
                        "factual_significance_assigned": False,
                        "causation_assigned": False,
                    }
                ],
            }
        ],
    )
    monkeypatch.setattr(
        workspace,
        "list_uncertain_executions",
        lambda limit, offset: {
            "executions": [
                {
                    "execution_id": "execution-a",
                    "case_id": "case-a",
                    "governance_action": "execute_browsertrix_production_capture",
                    "confirmation_sha256": "must-not-leak",
                    "delegate_service": "must-not-leak",
                    "state": "uncertain",
                    "state_version": 2,
                    "ledger_consistent": True,
                    "result_envelope_exists": False,
                    "automatic_retry": False,
                    "delegate_invocation_available": False,
                    "history": [{"metadata": {"secret": "must-not-leak"}}],
                }
            ]
        },
    )


def test_v38_8_builds_safe_read_only_workspace(monkeypatch):
    _patch_populated(monkeypatch)
    result = workspace.build_public_discovery_capture_workspace()
    assert result["schema"] == "socmint.public_discovery_capture_workspace.v38_8"
    assert result["status"] == "ready"
    assert result["read_only"] is True
    assert result["summary"]["blocked_gate_count"] == 1
    assert result["summary"]["passive_candidate_count"] == 1
    assert result["summary"]["accepted_artifact_count"] == 1
    assert result["summary"]["active_or_claimed_enablement_count"] == 1
    assert result["summary"]["support_eligible_capture_count"] == 1
    assert result["summary"]["uncertain_execution_count"] == 1
    assert {item["key"] for item in result["findings"]} == {
        "blocked_discovery_gate",
        "quarantined_passive_candidate",
        "synthetic_provenance_incomplete",
        "capture_candidate_review_pending",
        "out_of_scope_capture",
        "mirror_proposal_unconfirmed",
        "browsertrix_enablement_active",
        "execution_outcome_uncertain",
    }
    controls = result["controls"]
    assert controls["write_actions_exposed_by_workspace"] == []
    for key in (
        "automatic_collection",
        "automatic_retry",
        "automatic_artifact_acceptance",
        "automatic_source_independence_assessment",
        "automatic_observation_promotion",
        "automatic_truth_assignment",
        "automatic_entity_merge",
        "automatic_claim_approval",
        "automatic_dossier_mutation",
        "automatic_import_staging",
        "automatic_export",
        "automatic_publication",
    ):
        assert controls[key] is False


def test_v38_8_payload_omits_sensitive_values(monkeypatch):
    _patch_populated(monkeypatch)
    result = workspace.build_public_discovery_capture_workspace()
    rendered = repr(result)
    for forbidden in (
        "must-not-leak",
        "authorization_binding",
        "authorization_reference",
        "confirmation_sha256",
        "approved_storage_root",
        "'command':",
        '"command":',
    ):
        assert forbidden not in rendered
    assert result["artifact_inventory"][0]["content_sha256_prefix"] == "a" * 16
    assert result["source_inventory"][0]["content_sha256_prefix"] == "a" * 16
    assert result["capture_triage_inventory"][0][
        "factual_significance_assigned"
    ] is False
    assert result["capture_triage_inventory"][0]["causation_assigned"] is False


def test_v38_8_empty_workspace_is_safe(monkeypatch):
    _patch_empty(monkeypatch)
    result = workspace.build_public_discovery_capture_workspace()
    assert result["status"] == "ready"
    assert result["summary"]["finding_count"] == 0
    assert result["findings"] == []
    assert result["uncertain_execution_inventory"] == []
