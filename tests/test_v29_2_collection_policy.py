from datetime import datetime, timedelta, timezone

from src.socmint.collection_job_contract_v29_1 import create_collection_job_contract
from src.socmint.collection_policy_v29_2 import create_collection_policy, evaluate_collection_job_policy, revise_collection_policy
from src.socmint.collection_policy_workspace_v29_2 import build_collection_policy_workspace


def test_v29_2_policy_allow_deny_revision_and_workspace(tmp_path):
    from src.socmint import database
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    job = create_collection_job_contract(actor="admin", connector="public_web", target_value="alice", target_type="username", case_id="case-a", entity_id="entity-a", source_id="source-a", authorization_binding={"request_id":"request-1"}, purpose="investigation", idempotency_key="idem-1", legacy_scan_job_id=None, reason="create", confirmed=True)
    policy = create_collection_policy(actor="admin", name="Public Web", description="approved", permitted_source_classes=["public_web"], permitted_purposes=["investigation"], jurisdictions=["CA"], case_ids=["case-a"], entity_ids=[], source_ids=[], deny_rules=[], exclusions=[], valid_from="", expires_at=(datetime.now(timezone.utc)+timedelta(days=90)).isoformat(), review_at=(datetime.now(timezone.utc)+timedelta(days=10)).isoformat(), reason="define", confirmed=True)
    assert policy["status"] == "collection_policy_created"
    allowed = evaluate_collection_job_policy(actor="admin", collection_job_id=job["collection_job_id"], jurisdiction="CA", reason="evaluate", confirmed=True)
    assert allowed["status"] == "collection_policy_evaluated"
    assert allowed["evaluation"]["decision"] == "allow"
    revised = revise_collection_policy(policy["policy_id"], actor="admin", definition={"name":"Public Web v2","description":"revised","permitted_source_classes":["public_web"],"permitted_purposes":["investigation"],"jurisdictions":["CA"],"case_ids":["case-a"],"entity_ids":[],"source_ids":[],"deny_rules":[{"field":"target_value","value":"alice"}],"exclusions":[],"valid_from":None,"expires_at":None,"review_at":None}, reason="revise", confirmed=True)
    assert revised["status"] == "collection_policy_revised"
    denied = evaluate_collection_job_policy(actor="admin", collection_job_id=job["collection_job_id"], jurisdiction="CA", reason="reevaluate", confirmed=True)
    assert denied["evaluation"]["decision"] == "deny"
    assert denied["deny_overrides_allow"] is True
    result = build_collection_policy_workspace(review_due_within_days=30)
    assert result["active_policy_count"] == 1
    assert result["evaluation_count"] == 2
    assert result["evaluation_decision_counts"] == {"allow":1,"deny":1}
    assert result["deny_overrides_allow"] is True
    assert result["evaluation_mutates_collection_job"] is False
    assert result["connector_execution_available"] is False


def test_v29_2_blocks_missing_scope_and_duplicate_name(tmp_path):
    from src.socmint import database
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    first = create_collection_policy(actor="admin", name="Policy", description="", permitted_source_classes=["public_web"], permitted_purposes=["investigation"], jurisdictions=["CA"], case_ids=["case-a"], entity_ids=[], source_ids=[], deny_rules=[], exclusions=[], valid_from="", expires_at="", review_at="", reason="define", confirmed=True)
    duplicate = create_collection_policy(actor="admin", name="Policy", description="", permitted_source_classes=["public_web"], permitted_purposes=["investigation"], jurisdictions=["CA"], case_ids=["case-a"], entity_ids=[], source_ids=[], deny_rules=[], exclusions=[], valid_from="", expires_at="", review_at="", reason="define", confirmed=True)
    assert first["status"] == "collection_policy_created"
    assert duplicate["status"] == "blocked"
