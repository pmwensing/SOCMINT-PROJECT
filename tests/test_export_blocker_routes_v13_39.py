from src.socmint.wsgi import app

CSRF_TOKEN = "test-csrf-token"


def _login(client):
    with client.session_transaction() as sess:
        sess["user"] = "operator"
        sess["_csrf_token"] = CSRF_TOKEN


def test_export_pack_summary_route_surfaces_policy_blockers():
    client = app.test_client()
    _login(client)

    response = client.post(
        "/api/v1/dossier-builder/v3/export-pack/summary",
        json={
            "subject": {
                "subject_id": "subject-route-139",
                "display_name": "Route Subject",
                "case_id": "case-route-139",
            },
            "evidence": [
                {
                    "evidence_id": "ev-route-1",
                    "claim_id": "claim-route",
                    "source": "public_profile",
                    "confidence": 0.95,
                    "artifact_id": "art-route-1",
                    "review_state": "unreviewed",
                }
            ],
            "analyst_reviewed": True,
        },
        headers={"X-CSRF-Token": CSRF_TOKEN},
    )

    payload = response.get_json()

    assert response.status_code == 200
    assert payload["ready"] is False
    assert payload["blocker_count"] == 2
    assert set(payload["blocker_codes"]) == {"unreviewed_assertions", "single_source_claims"}


def test_export_gate_decision_route_surfaces_verification_summary():
    client = app.test_client()
    _login(client)

    response = client.get("/api/v1/dossier-builder/v3/export-gate/case-route-139/subject-route-139/decision")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["decision"] == "deny"
    assert "verification_summary" in payload
    assert payload["verification_summary"]["total_checks"] == 3


def test_export_blockers_ui_route_renders_operator_panel():
    client = app.test_client()
    _login(client)

    response = client.get("/dossier/export-blockers?case_id=case-route-139&subject_id=subject-route-139")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Export Blockers" in body
    assert "case-route-139 / subject-route-139" in body
    assert "Verification Checks" in body
