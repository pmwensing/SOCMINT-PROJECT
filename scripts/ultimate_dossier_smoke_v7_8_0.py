from __future__ import annotations

import os
import tempfile

from socmint import database as db
from socmint.command_center_routes import register_command_center_routes
from socmint.connector_normalizers import normalize_connector_output
from socmint.connector_runtime_routes import register_connector_runtime_routes
from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import register_full_report_retention_routes
from socmint.spine import create_subject
from socmint.spine import correlate_subject
from socmint.spine_intelligence_routes import register_spine_intelligence_routes
from socmint.ultimate_dossier import assertions_csv
from socmint.ultimate_dossier import ultimate_dossier_payload
from socmint.ultimate_dossier_routes import register_ultimate_dossier_routes


def _run_with_result(subject_id: int, connector: str, seed_type: str, seed_value: str, raw_result: dict) -> int:
    seed = db.add_spine_seed(
        subject_id=subject_id,
        seed_type=seed_type,
        raw_value=seed_value,
        normalized_value=seed_value,
        pii_hash=f"smoke-{connector}-{seed_type}",
    )
    from socmint.spine import run_connector_for_seed
    from socmint.spine import HIGH_VALUE_CONNECTORS

    return run_connector_for_seed(subject_id, seed, connector, HIGH_VALUE_CONNECTORS[connector])


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-v780-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        subject_id = create_subject(
            "Ultimate Entity Human QA v7.8.0",
            [
                {"type": "username", "value": "ultimateqa"},
                {"type": "email", "value": "ultimateqa@example.com"},
                {"type": "phone", "value": "+15555550123"},
                {"type": "url", "value": "https://example.org/ultimateqa"},
            ],
        )

        assert normalize_connector_output(
            "sherlock",
            "ultimateqa",
            "username",
            {"status": "completed", "stdout": "Twitter: found\nhttps://x.com/ultimateqa"},
        )[0]["type"] == "profile_url"
        assert normalize_connector_output(
            "phoneinfoga",
            "+15555550123",
            "phone",
            {"status": "completed", "stdout": "Country: Canada\nCarrier: ExampleTel\nLine Type: mobile"},
        )[0]["type"] == "phone_country"
        assert normalize_connector_output(
            "h8mail",
            "ultimateqa@example.com",
            "email",
            {"status": "completed", "stdout": "breach found ExampleLeak database"},
        )[0]["type"] == "exposure_indicator"

        _run_with_result(
            subject_id,
            "sherlock",
            "username",
            "ultimateqa",
            {"status": "completed", "stdout": "Twitter: found\nhttps://x.com/ultimateqa", "stderr": "", "findings": []},
        )
        _run_with_result(
            subject_id,
            "phoneinfoga",
            "phone",
            "+15555550123",
            {"status": "completed", "stdout": "Country: Canada\nCarrier: ExampleTel\nLine Type: mobile", "stderr": "", "findings": []},
        )
        _run_with_result(
            subject_id,
            "h8mail",
            "email",
            "ultimateqa@example.com",
            {"status": "completed", "stdout": "breach found ExampleLeak database", "stderr": "", "findings": []},
        )
        correlate_subject(subject_id)

        assertions = db.list_spine_assertions(subject_id)
        assert len(assertions) >= 3
        for assertion in assertions:
            db.validate_spine_assertion(assertion.id, "ultimate-smoke", "confirmed", "smoke confirm")

        payload = ultimate_dossier_payload(subject_id)
        assert payload["schema"] == "socmint.ultimate_entity_human_dossier.v7_8_0"
        assert payload["summary"]["assertion_count"] >= 3
        assert payload["resolution"]["dossier_kind"] in {"human_subject", "entity_human_hybrid"}
        assert payload["resolution"]["identity_confidence"] > 0
        assert payload["traceability"]
        assert payload["timeline"]
        assert payload["narrative"]["executive_summary"]
        assert payload["exports"]["csv"].endswith("assertions.csv")
        csv_text = assertions_csv(payload)
        assert "profile_url" in csv_text
        assert "phone_country" in csv_text
        assert "exposure_indicator" in csv_text

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="ultimate-dossier-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)
        register_command_center_routes(app)
        register_connector_runtime_routes(app)
        register_spine_intelligence_routes(app)
        register_ultimate_dossier_routes(app)

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "ultimate-dossier-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "ultimate-csrf"

            html = client.get(f"/spine/subjects/{subject_id}/ultimate-dossier")
            assert html.status_code == 200
            text = html.get_data(as_text=True)
            assert "Ultimate Entity/Human SOCMINT Dossier" in text
            assert "Executive Summary" in text
            assert "Entity / Human Resolution" in text
            assert "Source Traceability" in text
            assert "Timeline" in text
            assert "Assertion CSV" in text

            api = client.get(f"/api/v1/spine/subjects/{subject_id}/ultimate-dossier")
            assert api.status_code == 200
            assert api.get_json()["schema"] == "socmint.ultimate_entity_human_dossier.v7_8_0"

            csv_response = client.get(f"/spine/subjects/{subject_id}/ultimate-dossier/assertions.csv")
            assert csv_response.status_code == 200
            assert "text/csv" in csv_response.content_type
            assert "profile_url" in csv_response.get_data(as_text=True)

        print("v7.8.0 ultimate dossier smoke passed")


if __name__ == "__main__":
    main()
