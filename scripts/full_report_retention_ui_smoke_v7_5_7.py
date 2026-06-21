from __future__ import annotations

import os
import re
import tempfile
import time

from socmint.dashboard import create_app
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow
from socmint.full_report_history import register_full_report_history_routes
from socmint.full_report_retention import register_full_report_retention_routes

SUBJECT_ID = 7570


def export_three_reports(client, csrf_headers: dict[str, str]) -> None:
    for _ in range(3):
        response = client.post(
            f"/spine/subjects/{SUBJECT_ID}/dossier-v2/export/run",
            headers=csrf_headers,
            follow_redirects=False,
        )
        assert response.status_code in {301, 302, 303, 307, 308}
        time.sleep(1.1)


def export_names(client) -> list[str]:
    response = client.get(f"/api/v1/spine/subjects/{SUBJECT_ID}/full-report/history")
    assert response.status_code == 200
    return [item["name"] for item in response.get_json()["exports"]]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-ui-v757-") as tmp:
        os.chdir(tmp)
        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="retention-ui-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)
        register_full_report_history_routes(app)
        register_full_report_retention_routes(app)

        with app.test_client() as client:
            csrf = "retention-ui-smoke-csrf-token"
            with client.session_transaction() as session:
                session["user"] = "retention-ui-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = csrf
            csrf_headers = {"X-CSRF-Token": csrf}

            export_three_reports(client, csrf_headers)
            names = export_names(client)
            assert len(names) >= 3
            latest_name = names[0]
            old_name = names[-1]

            page = client.get(
                f"/spine/subjects/{SUBJECT_ID}/full-report/retention?keep_latest=1"
            )
            assert page.status_code == 200
            text = page.get_data(as_text=True)
            assert "Full Report Retention" in text
            assert "Pin important" in text
            assert "Dry-run retention" in text
            assert "Apply retention delete candidates" in text
            assert "Confirm:" in text
            assert f"placeholder='{old_name}'" in text or old_name in text

            # Pin through the browser UI route.
            pin = client.post(
                f"/spine/subjects/{SUBJECT_ID}/full-report/pin",
                data={
                    "name": old_name,
                    "note": "ui smoke pin",
                    "keep_latest": "1",
                    "csrf_token": csrf,
                },
                follow_redirects=True,
            )
            assert pin.status_code == 200
            assert "Pinned export" in pin.get_data(as_text=True)

            # Delete without exact confirmation must be blocked by UI confirmation guard.
            bad_delete = client.post(
                f"/spine/subjects/{SUBJECT_ID}/full-report/delete",
                data={
                    "name": old_name,
                    "confirm_name": "wrong",
                    "keep_latest": "1",
                    "csrf_token": csrf,
                },
                follow_redirects=True,
            )
            assert bad_delete.status_code == 200
            assert (
                "Delete blocked: confirmation did not match export filename"
                in bad_delete.get_data(as_text=True)
            )
            assert old_name in export_names(client)

            # Delete pinned export with exact confirmation must still be blocked by retention safety.
            pinned_delete = client.post(
                f"/spine/subjects/{SUBJECT_ID}/full-report/delete",
                data={
                    "name": old_name,
                    "confirm_name": old_name,
                    "keep_latest": "1",
                    "csrf_token": csrf,
                },
                follow_redirects=True,
            )
            assert pinned_delete.status_code == 200
            assert "Delete blocked: export_pinned" in pinned_delete.get_data(
                as_text=True
            )
            assert old_name in export_names(client)

            # Dry-run through the browser UI route.
            dry_run = client.post(
                f"/spine/subjects/{SUBJECT_ID}/full-report/apply-retention",
                data={"keep_latest": "1", "dry_run": "true", "csrf_token": csrf},
                follow_redirects=True,
            )
            assert dry_run.status_code == 200
            assert re.search(
                r"Dry-run complete: [1-9][0-9]* delete candidate",
                dry_run.get_data(as_text=True),
            )

            # Applying real retention without APPLY must be blocked.
            blocked_apply = client.post(
                f"/spine/subjects/{SUBJECT_ID}/full-report/apply-retention",
                data={
                    "keep_latest": "1",
                    "dry_run": "false",
                    "confirm_apply": "NO",
                    "csrf_token": csrf,
                },
                follow_redirects=True,
            )
            assert blocked_apply.status_code == 200
            assert (
                "Apply blocked: type APPLY to confirm deletion"
                in blocked_apply.get_data(as_text=True)
            )

            # Unpin old export through UI.
            unpin = client.post(
                f"/spine/subjects/{SUBJECT_ID}/full-report/unpin",
                data={"name": old_name, "keep_latest": "1", "csrf_token": csrf},
                follow_redirects=True,
            )
            assert unpin.status_code == 200
            assert "Unpinned export" in unpin.get_data(as_text=True)

            # Delete an unpinned old export through the UI with exact confirmation.
            delete_names = export_names(client)
            candidate = next(
                name for name in reversed(delete_names) if name != latest_name
            )
            delete_response = client.post(
                f"/spine/subjects/{SUBJECT_ID}/full-report/delete",
                data={
                    "name": candidate,
                    "confirm_name": candidate,
                    "keep_latest": "1",
                    "csrf_token": csrf,
                },
                follow_redirects=True,
            )
            assert delete_response.status_code == 200
            assert "Deleted" in delete_response.get_data(as_text=True)
            assert candidate not in export_names(client)

        print("v7.5.7 retention UI action smoke passed")


if __name__ == "__main__":
    main()
