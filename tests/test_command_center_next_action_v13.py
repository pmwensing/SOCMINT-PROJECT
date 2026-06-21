from socmint.command_center_next_action_v13 import command_center_next_action_payload


def test_next_action_blocks_without_subject():
    payload = {
        "schema": "test",
        "summary": {},
        "subjects": [],
        "targets": [],
        "jobs": [],
    }

    result = command_center_next_action_payload(payload)

    assert result["schema"] == "socmint.command_center_next_action.v13_0"
    assert result["dossier_readiness"]["state"] == "blocked"
    assert result["next_best_action"]["key"] == "create_subject"


def test_next_action_requires_seed_after_subject():
    payload = {
        "schema": "test",
        "summary": {"findings_count": 0, "report_count": 0},
        "subjects": [{"id": 42, "label": "Subject"}],
        "targets": [],
        "jobs": [],
    }

    result = command_center_next_action_payload(payload)

    assert result["dossier_readiness"]["state"] == "blocked"
    assert result["next_best_action"]["key"] == "add_seed"


def test_next_action_generates_dossier_after_findings():
    payload = {
        "schema": "test",
        "summary": {"findings_count": 3, "report_count": 0},
        "subjects": [{"id": 42, "label": "Subject"}],
        "targets": [{"id": 1, "value": "seed", "type": "username"}],
        "jobs": [],
        "guided_investigation": {"action_count": 0},
    }

    result = command_center_next_action_payload(payload)

    assert result["dossier_readiness"]["state"] == "draft_ready"
    assert result["next_best_action"]["key"] == "generate_dossier"
    assert result["next_best_action"]["href"] == "/spine/subjects/42/full-report"


def test_next_action_exports_when_report_exists():
    payload = {
        "schema": "test",
        "summary": {"findings_count": 3, "report_count": 1},
        "subjects": [{"id": 42, "label": "Subject"}],
        "targets": [{"id": 1, "value": "seed", "type": "username"}],
        "jobs": [],
        "guided_investigation": {"action_count": 0},
    }

    result = command_center_next_action_payload(payload)

    assert result["dossier_readiness"]["state"] == "exported"
    assert result["next_best_action"]["key"] == "export_case_package"
