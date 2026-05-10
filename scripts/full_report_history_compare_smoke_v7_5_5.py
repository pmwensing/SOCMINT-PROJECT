from __future__ import annotations

import os
import tempfile
from pathlib import Path

from socmint.dashboard import create_app
from socmint.entity_dossier_v2 import export_full_entity_dossier_v2
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import compare_full_report_exports
from socmint.full_report_history import full_report_export_history
from socmint.full_report_history import register_full_report_history_routes


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-v755-") as tmp:
        os.chdir(tmp)
        subject_id = 755

        first = export_full_entity_dossier_v2(subject_id)
        second = export_full_entity_dossier_v2(subject_id)

        history = full_report_export_history(subject_id)
        assert history["schema"] == "socmint.full_report_export_history.v7_5_5"
        assert history["subject_id"] == subject_id
        assert history["count"] >= 2
        assert history["exports"][0]["name"].endswith("-EXPORT.json")
        assert history["exports"][0]["artifact_count"] >= 5
        assert "zip_bundle" in history["exports"][0]["artifact_roles"]

        compare = compare_full_report_exports(subject_id)
        assert compare["schema"] == "socmint.full_report_export_compare.v7_5_5"
        assert compare["available"] is True
        assert compare["right"]["name"] == history["exports"][0]["name"]
        assert compare["left"]["name"] == history["exports"][1]["name"]
        assert "evidence_count" in compare["score_delta"]
        assert "unchanged" in compare["artifact_role_delta"]

        named_compare = compare_full_report_exports(
            subject_id,
            left=Path(first["result_path"]).name,
            right=Path(second["result_path"]).name,
        )
        assert named_compare["available"] is True

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="history-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "history-smoke"
                session["is_admin"] = True
                session["role"] = "admin"

            history_response = client.get(
                f"/api/v1/spine/subjects/{subject_id}/full-report/history"
            )
            assert history_response.status_code == 200
            history_json = history_response.get_json()
            assert history_json["count"] >= 2

            compare_response = client.get(
                f"/api/v1/spine/subjects/{subject_id}/full-report/compare"
            )
            assert compare_response.status_code == 200
            assert compare_response.get_json()["available"] is True

            panel_response = client.get(
                f"/spine/subjects/{subject_id}/full-report/history"
            )
            assert panel_response.status_code == 200
            panel_text = panel_response.get_data(as_text=True)
            assert "Full Report Export History" in panel_text
            assert "Compare Previous Reports" in panel_text
            assert "Delta" in panel_text

        print("v7.5.5 history compare smoke passed")


if __name__ == "__main__":
    main()
