import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "release/V38_0_LAWFUL_PUBLIC_WEB_DISCOVERY_PLANNING_CONTRACT.json"
ROADMAP_PATH = ROOT / "release/V38_0_LAWFUL_PUBLIC_WEB_DISCOVERY_ROADMAP.md"
INVENTORY_PATH = ROOT / "release/V38_0_EXISTING_CAPABILITY_INVENTORY.md"
OWNERSHIP_PATH = ROOT / "release/V38_0_SCHEMA_OWNERSHIP_MAP.md"
ENTRY_GATE_PATH = ROOT / "release/V38_0_PLANNING_ENTRY_GATE.md"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_v38_0_contract_is_planning_only_and_complete():
    contract = _contract()
    assert contract["schema"] == "socmint.v38.planning_contract.v38_0"
    assert contract["version"] == "v38.0.0"
    assert contract["status"] == "planning_gate"
    assert contract["planning_only"] is True
    assert [item["slice"] for item in contract["roadmap"]] == [
        f"v38.{index}" for index in range(10)
    ]
    gate = contract["runtime_gate"]
    assert gate["runtime_implemented_in_v38_0"] is False
    assert gate["migration_implemented_in_v38_0"] is False
    assert gate["runtime_allowed_after_v38_0_merge"] is True
    assert (
        gate["next_action"]
        == "implement_v38_1_discovery_request_and_crawl_manifest_gate"
    )


def test_v38_0_capture_governance_precedes_live_network_adapters():
    contract = _contract()
    roadmap = {item["slice"]: item["capability"] for item in contract["roadmap"]}
    assert "synthetic capture envelope" in roadmap["v38.4"]
    assert "v29 artifact acceptance" in roadmap["v38.4"]
    assert "v36 source registration" in roadmap["v38.4"]
    assert "no live-network execution" in roadmap["v38.4"]
    assert "HTTP crawler adapter" in roadmap["v38.5"]
    assert "Browsertrix capture" in roadmap["v38.6"]

    live_gate = contract["live_network_execution_gate"]
    for slice_name in ("v38_1", "v38_2", "v38_3", "v38_4"):
        assert live_gate[f"live_network_allowed_in_{slice_name}"] is False
    assert live_gate["synthetic_capture_provenance_gate_slice"] == "v38.4"
    assert live_gate["scrapy_live_network_earliest_slice"] == "v38.5"
    assert live_gate["browsertrix_live_network_earliest_slice"] == "v38.6"
    assert {
        "synthetic_capture_envelope",
        "deterministic_content_sha256",
        "provenance_manifest",
        "accepted_v29_artifact_binding",
        "registered_v36_source_binding",
        "explicit_v37_import_handoff",
        "duplicate_and_quarantine_non_inflation",
    } == set(live_gate["required_v38_4_proofs"])


def test_v38_0_contract_reuses_authorities_and_blocks_unsafe_automation():
    contract = _contract()
    required_authorities = {
        "case_scope_and_privacy",
        "search_pack",
        "public_source_policy",
        "collection_jobs",
        "collection_policy",
        "adapter_contract",
        "artifact_evidence",
        "collection_quality",
        "action_execution",
        "source_registry",
        "source_independence",
        "operational_imports",
        "analyst_workflow",
        "search_reporting",
        "audit",
        "export_and_publication",
    }
    assert required_authorities.issubset(contract["authoritative_reuse"])
    assert contract["prohibited_duplication"]
    assert all(value is False for value in contract["prohibited_duplication"].values())
    assert contract["prohibited_automation"]
    assert all(value is False for value in contract["prohibited_automation"].values())
    assert contract["production_invariants"]
    assert all(value is True for value in contract["production_invariants"].values())


def test_v38_0_required_baselines_and_planning_artifacts_exist():
    contract = _contract()
    closure_path = ROOT / contract["required_baselines"]["v37_closure_contract"]
    assert closure_path.is_file()
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    assert closure["status"] == "closed"
    assert closure["closure"]["v37_closed"] is True
    required_paths = contract["required_baselines"][
        "governance_and_case_paths_required"
    ]
    assert required_paths
    missing = [path for path in required_paths if not (ROOT / path).is_file()]
    assert missing == []
    for path in (
        ROADMAP_PATH,
        INVENTORY_PATH,
        OWNERSHIP_PATH,
        ENTRY_GATE_PATH,
    ):
        assert path.is_file(), path


def test_v38_0_planning_documents_preserve_scope_and_access_boundaries():
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8").lower()
    inventory = INVENTORY_PATH.read_text(encoding="utf-8").lower()
    ownership = OWNERSHIP_PATH.read_text(encoding="utf-8").lower()
    gate = ENTRY_GATE_PATH.read_text(encoding="utf-8").lower()

    for marker in (
        "passive archive",
        "synthetic capture/provenance proof",
        "operator-triggered",
        "no arbitrary off-domain",
        "synthetic local http/archive fixtures",
        "scrapy may receive a live-network path no earlier than v38.5",
        "browsertrix may receive a live-network path no earlier than v38.6",
    ):
        assert marker in roadmap

    for marker in (
        "private-account",
        "credential dumps",
        "tor",
        "automatic observation promotion",
    ):
        assert marker in inventory

    for marker in (
        "no second collection-job",
        "no second durable action ledger",
        "no second artifact",
        "no second source registry",
        "no mutable canonical fact or truth table",
    ):
        assert marker in ownership

    for marker in (
        "v38.0 is planning-only",
        "no url is fetched",
        "cowdy-only issue collection",
        "failed, blocked, or uncertain executions are never silently retried",
        "v38.1 through v38.4 must not create or enable a live third-party crawler",
        "scrapy live-network execution is eligible no earlier than v38.5",
        "browsertrix live-network execution is eligible no earlier than v38.6",
        "implement_v38_1_discovery_request_and_crawl_manifest_gate",
    ):
        assert marker in gate


def test_v38_0_introduces_no_runtime_or_migration_files():
    runtime_matches = [
        path
        for path in (ROOT / "src/socmint").rglob("*")
        if path.is_file() and "v38_0" in path.name.lower()
    ]
    migration_roots = [ROOT / "migrations", ROOT / "alembic"]
    migration_matches = [
        path
        for base in migration_roots
        if base.exists()
        for path in base.rglob("*")
        if path.is_file() and "v38_0" in path.name.lower()
    ]
    assert runtime_matches == []
    assert migration_matches == []
