from __future__ import annotations

import os
import tempfile
import time

from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import register_full_report_retention_routes


SUBJECT_ID = 7560


def assert_contains(text: str, expected: str) -> None:
    assert expected in text, f"expected page to contain {expected!r}"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-human-v756-") as tmp:
        os.chdir(tmp)

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="human-equivalent-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)

        with app.test_client() as client:
            csrf = "human-equivalent-csrf-token"
            with client.session_transaction() as session:
                session["user"] = "human-equivalent-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = csrf
            csrf_headers = {"X-CSRF-Token": csrf}

            # 1-2. Human opens the subject dossier page.
            dossier = client.get(f"/spine/subjects/{SUBJECT_ID}/dossier")
            assert dossier.status_code == 200
            dossier_text = dossier.get_data(as_text=True)
            assert_contains(dossier_text, "Full Entity Profile Dossier v2")
            assert_contains(dossier_text, "Run Full Report")
            assert_contains(dossier_text, "Export History")
            assert_contains(dossier_text, "Retention / Pins")

            # 3. Human clicks Run Full Report three times.
            result_names = []
            for _ in range(3):
                response = client.post(
                    f"/spine/subjects/{SUBJECT_ID}/dossier-v2/export/run",
                    headers=csrf_headers,
                    follow_redirects=False,
                )
                assert response.status_code in {301, 302, 303, 307, 308}
                time.sleep(1.1)

                latest = client.get(
                    f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/latest"
                )
                assert latest.status_code == 200
                latest_json = latest.get_json()
                assert latest_json["available"] is True
                result_names.append(latest_json["result_name"])

            assert len(set(result_names)) == 3

            # 4. Human opens Export History.
            history_page = client.get(
                f"/spine/subjects/{SUBJECT_ID}/full-report/history"
            )
            assert history_page.status_code == 200
            history_text = history_page.get_data(as_text=True)
            assert_contains(history_text, "Full Report Export History")
            assert_contains(history_text, "Compare Previous Reports")

            history_api = client.get(
                f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/history"
            )
            assert history_api.status_code == 200
            history = history_api.get_json()
            assert history["count"] >= 3
            history_names = [item["name"] for item in history["exports"]]

            # 5. Human clicks Compare Previous Reports.
            compare = client.get(
                f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/compare"
            )
            assert compare.status_code == 200
            compare_json = compare.get_json()
            assert compare_json["available"] is True
            assert "score_delta" in compare_json
            assert "artifact_role_delta" in compare_json

            # 6. Human opens Retention / Pins.
            retention_page = client.get(
                f"/spine/subjects/{SUBJECT_ID}/full-report/retention"
            )
            assert retention_page.status_code == 200
            retention_text = retention_page.get_data(as_text=True)
            assert_contains(retention_text, "Full Report Retention")
            assert_contains(retention_text, "Delete Candidates")

            # 7. Human pins an important older export.
            pinned_name = history_names[-1]
            pin = client.post(
                f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/pin",
                json={
                    "name": pinned_name,
                    "note": "human equivalent important baseline",
                },
                headers=csrf_headers,
            )
            assert pin.status_code == 200
            assert pin.get_json()["ok"] is True

            # 8. Human tries deleting pinned export; it must block.
            blocked_delete = client.post(
                f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/delete",
                json={"name": pinned_name},
                headers=csrf_headers,
            )
            assert blocked_delete.status_code == 409
            assert blocked_delete.get_json()["error"] == "export_pinned"

            # 9. Human dry-runs retention.
            dry_run = client.post(
                f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/apply-retention",
                json={"keep_latest": 1, "dry_run": True},
                headers=csrf_headers,
            )
            assert dry_run.status_code == 200
            dry_json = dry_run.get_json()
            assert dry_json["dry_run"] is True
            assert dry_json["delete_count"] >= 1

            # 10. Human deletes an unpinned old export.
            retention = client.get(
                f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/retention?keep_latest=1"
            )
            assert retention.status_code == 200
            delete_candidates = retention.get_json()["delete"]
            unpinned_candidate = next(
                item for item in delete_candidates if item["name"] != pinned_name
            )
            delete_name = unpinned_candidate["name"]
            delete_response = client.post(
                f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/delete",
                json={"name": delete_name},
                headers=csrf_headers,
            )
            assert delete_response.status_code == 200
            assert delete_response.get_json()["ok"] is True

            # 11. Human confirms history updates.
            final_history_response = client.get(
                f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/history"
            )
            assert final_history_response.status_code == 200
            final_names = {
                item["name"] for item in final_history_response.get_json()["exports"]
            }
            assert delete_name not in final_names
            assert pinned_name in final_names

            final_dossier = client.get(f"/spine/subjects/{SUBJECT_ID}/dossier")
            assert final_dossier.status_code == 200
            final_text = final_dossier.get_data(as_text=True)
            assert_contains(final_text, "Latest Full Report Export")
            assert_contains(final_text, "Export History")
            assert_contains(final_text, "Retention / Pins")

        print("v7.5.6 full human-equivalent smoke passed")


if __name__ == "__main__":
    main()
