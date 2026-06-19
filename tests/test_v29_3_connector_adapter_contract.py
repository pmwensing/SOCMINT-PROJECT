from src.socmint.connector_adapter_contract_v29_3 import create_adapter_contract, evaluate_adapter_conformance, revise_adapter_contract
from src.socmint.connector_adapter_workspace_v29_3 import build_connector_adapter_workspace


def test_v29_3_adapter_contract_conformance_and_revision(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import connector_adapter_contract_v29_3 as contract
    from src.socmint import connector_adapter_workspace_v29_3 as workspace
    database.configure_database(f"sqlite:///{tmp_path / 'app.db'}")
    connector = {"connector_id":"connector-1","connector_status":"active","definition":{"name":"Demo"}}
    monkeypatch.setattr(contract, "find_connector", lambda connector_id: connector if connector_id == "connector-1" else None)
    monkeypatch.setattr(workspace, "current_connectors", lambda: [connector])
    created = create_adapter_contract(actor="admin", connector_id="connector-1", capabilities=["profile_lookup"], input_schema={"type":"object"}, output_schema={"type":"object"}, authorization_requirements={"scope":"read"}, rate_limit_metadata={"rpm":30}, error_classes=["network_error","output_error"], provenance_requirements={"required_fields":["source_url","acquired_at"]}, health_contract={"required_fields":["status","checked_at"]}, dossier_value_declaration={"finding_types":["profile"]}, reason="define", confirmed=True)
    assert created["status"] == "adapter_contract_created"
    evaluated = evaluate_adapter_conformance(actor="admin", adapter_contract_id=created["adapter_contract_id"], observed_capabilities=["profile_lookup"], observed_input_schema={"type":"object"}, observed_output_schema={"type":"object"}, observed_error_classes=["network_error","output_error"], observed_provenance_fields=["source_url","acquired_at"], observed_health_fields=["status","checked_at"], reason="evaluate", confirmed=True)
    assert evaluated["status"] == "adapter_conformance_evaluated"
    assert evaluated["evaluation"]["conformant"] is True
    revised = revise_adapter_contract(created["adapter_contract_id"], actor="admin", definition={"capabilities":["profile_lookup","media_lookup"],"input_schema":{"type":"object"},"output_schema":{"type":"object"},"authorization_requirements":{"scope":"read"},"rate_limit_metadata":{"rpm":20},"error_classes":["network_error"],"provenance_requirements":{"required_fields":["source_url"]},"health_contract":{"required_fields":["status"]},"dossier_value_declaration":{"finding_types":["profile","media"]}}, reason="revise", confirmed=True)
    assert revised["status"] == "adapter_contract_revised"
    result = build_connector_adapter_workspace()
    assert result["active_adapter_contract_count"] == 1
    assert result["conformance_evaluation_count"] == 1
    assert result["connector_execution_available"] is False
    assert result["new_connectors_added_for_breadth"] is False


def test_v29_3_blocks_invalid_error_class_and_nonconformance(tmp_path, monkeypatch):
    from src.socmint import database
    from src.socmint import connector_adapter_contract_v29_3 as contract
    database.configure_database(f"sqlite:///{tmp_path / 'blocked.db'}")
    monkeypatch.setattr(contract, "find_connector", lambda connector_id: {"connector_id":connector_id,"connector_status":"active","definition":{"name":"Demo"}})
    invalid = create_adapter_contract(actor="admin", connector_id="connector-1", capabilities=["lookup"], input_schema={}, output_schema={}, authorization_requirements={}, rate_limit_metadata={}, error_classes=["made_up"], provenance_requirements={}, health_contract={}, dossier_value_declaration={}, reason="define", confirmed=True)
    assert invalid["status"] == "blocked"
