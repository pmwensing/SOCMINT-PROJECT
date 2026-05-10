from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from socmint.dashboard import create_app
from socmint.entity_dossier_v2 import export_full_entity_dossier_v2
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import full_report_export_history
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import apply_retention
from socmint.full_report_retention import delete_export
from socmint.full_report_retention import pin_export
from socmint.full_report_retention import register_full_report_retention_routes
from socmint.full_report_retention import retention_plan
from socmint.full_report_retention import unpin_export


def make_export(subject_id: int) -> dict:
    result = export_full_entity_dossier_v2(subject_id)
    time.sleep(1.1)
    return result


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-v756-") as tmp:
        os.chdir(tmp)
        subject_id = 756

        first = make_export(subject_id)
        second = make_export(subject_id)
        third = make_export(subject_id)

        history = full_report_export_history(subject_id)
        assert history["count"] >= 3
        names = [item["name"] for item in history["exports"]]
        first_name = Path(first["result_path"]).name
        second_name = Path(second["result_path"]).name
        third_name = Path(third["result_path"]).name
        assert {first_name, second_name, third_name} <= set(names)

        pin = pin_export(subject_id, first_name, note="important baseline")
        assert pin["ok"] is True

        plan = retention_plan(subject_id, keep_latest=1)
        assert plan["schema"] == "socmint.full_report_retention.v7_5_6"
        assert plan["history_count"] >= 3
        assert plan["pinned_count"] == 1
        keep_names = {item["name"] for item in plan["keep"]}
        delete_names = {item["name"] for item in plan["delete"]}
        assert first_name in keep_names
        assert third_name in keep_names
        assert second_name in delete_names

        dry_run = apply_retention(subject_id, keep_latest=1, dry_run=True)
        assert dry_run["dry_run"] is True
        assert dry_run["delete_count"] >= 1

        blocked = delete_export(subject_id, first_name, force=False)
        assert blocked["ok"] is False
        assert blocked["error"] == "export_pinned"

        deleted = delete_export(subject_id, second_name, force=False)
        assert deleted["ok"] is True
        assert deleted["deleted_count"] >= 1

        after_delete = full_report_export_history(subject_id)
        after_names = {item["name"] for item in after_delete["exports"]}
        assert second_name not in after_names
        assert first_name in after_names
        assert third_name in after_names

        unpin = unpin_export(subject_id, first_name)
        assert unpin["ok"] is True
        final_plan = retention_plan(subject_id, keep_latest=1)
        assert final_plan["pinned_count"] == 0

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="retention-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)

        with app.test_client() as client:
            csrf = "retention-smoke-csrf-token"
            with client.session_transaction() as session:
                session["user"] = "retention-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = csrf
            csrf_headers = {"X-CSRF-Token": csrf}

            retention_response = client.get(
                f"/api/v1/spine/subjects/{subject_id}/full-report/retention?keep_latest=1"
            )
            assert retention_response.status_code == 200
            assert retention_response.get_json()["schema"] == "socmint.full_report_retention.v7_5_6"

            pin_response = client.post(
                f"/api/v1/spine/subjects/{subject_id}/full-report/pin",
                json={"name": first_name, "note": "route pin"},
                headers=csrf_headers,
            )
            assert pin_response.status_code == 200
            assert pin_response.get_json()["ok"] is True

            delete_response = client.post(
                f"/api/v1/spine/subjects/{subject_id}/full-report/delete",
                json={"name": first_name},
                headers=csrf_headers,
            )
            assert delete_response.status_code == 409
            assert delete_response.get_json()["error"] == "export_pinned"

            apply_response = client.post(
                f"/api/v1/spine/subjects/{subject_id}/full-report/apply-retention",
                json={"keep_latest": 1, "dry_run": True},
                headers=csrf_headers,
            )
            assert apply_response.status_code == 200
            assert apply_response.get_json()["dry_run"] is True

            ui_response = client.get(
                f"/spine/subjects/{subject_id}/full-report/retention"
            )
            assert ui_response.status_code == 200
            ui_text = ui_response.get_data(as_text=True)
            assert "Full Report Retention" in ui_text
            assert "Delete Candidates" in ui_text

        print("v7.5.6 retention smoke passed")


if __name__ == "__main__":
    main()
