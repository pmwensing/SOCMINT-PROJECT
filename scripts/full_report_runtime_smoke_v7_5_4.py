from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from socmint.dashboard import create_app
from socmint.entity_dossier_v2 import export_full_entity_dossier_v2
from socmint.full_report_alias import latest_full_report_export
from socmint.full_report_alias import register_full_report_aliases
from socmint.full_report_browser import register_full_report_browser_flow


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_manifest_hashes(manifest: dict) -> None:
    files = manifest.get("files") or []
    assert files, "manifest has no files"
    verified_roles = []

    for entry in files:
        role = entry["role"]
        path = Path(entry["path"])
        expected_hash = entry["sha256"]
        expected_size = entry["size_bytes"]
        assert path.exists(), f"{role} missing: {path}"

        if role == "export_manifest":
            # The manifest contains an entry for itself and is then rewritten
            # after bundle metadata is appended. Exact self size/hash equality
            # is self-referential and not stable. Validate presence, structure,
            # parseability, and digest shape instead.
            assert path.stat().st_size > 0, "export_manifest is empty"
            assert len(expected_hash) == 64, "export_manifest digest malformed"
            assert json.loads(path.read_text())["schema"].endswith("v7_5_1")
            continue

        assert path.stat().st_size == expected_size, f"{role} size mismatch"
        assert sha256_file(path) == expected_hash, f"{role} sha256 mismatch"
        verified_roles.append(role)

    assert "dossier_json" in verified_roles
    assert "dossier_markdown" in verified_roles
    assert "dossier_html" in verified_roles
    assert "zip_bundle" in verified_roles


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="socmint-v754-") as tmp:
        os.chdir(tmp)
        subject_id = 754

        result = export_full_entity_dossier_v2(subject_id)
        manifest_path = Path(result["manifest_path"])
        manifest = json.loads(manifest_path.read_text())
        assert_manifest_hashes(manifest)

        latest = latest_full_report_export(subject_id)
        assert latest["available"] is True
        assert latest["html_name"] == Path(result["html_path"]).name
        assert latest["manifest_name"] == manifest_path.name
        assert latest["zip_name"] == Path(result["zip_path"]).name

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="runtime-smoke")
        register_full_report_aliases(app)
        register_full_report_browser_flow(app)

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "runtime-smoke"
                session["is_admin"] = True
                session["role"] = "admin"

            latest_response = client.get(
                f"/api/v1/spine/subjects/{subject_id}/full-report/latest"
            )
            assert latest_response.status_code == 200
            assert latest_response.get_json()["available"] is True

            panel_response = client.get(
                f"/spine/subjects/{subject_id}/full-report/view"
            )
            assert panel_response.status_code == 200
            panel_text = panel_response.get_data(as_text=True)
            assert "Full Report Export" in panel_text
            assert "Open latest HTML report" in panel_text
            assert "SHA-256" in panel_text

            open_response = client.get(
                f"/spine/subjects/{subject_id}/full-report/open",
                follow_redirects=False,
            )
            assert open_response.status_code in {301, 302, 303, 307, 308}
            assert "full-report/artifact" in open_response.headers["Location"]

            html_response = client.get(open_response.headers["Location"])
            assert html_response.status_code == 200
            assert "text/html" in html_response.headers.get("Content-Type", "")
            assert "Full Entity Profile Dossier v2" in html_response.get_data(
                as_text=True
            )

            manifest_response = client.get(
                f"/spine/subjects/{subject_id}/full-report/artifact"
                f"?name={latest['manifest_name']}"
            )
            assert manifest_response.status_code == 200
            assert "application/json" in manifest_response.headers.get(
                "Content-Type", ""
            )
            assert (
                "socmint.full_entity_profile_dossier_manifest.v7_5_1"
                in manifest_response.get_data(as_text=True)
            )

        print("v7.5.4 runtime smoke passed")


if __name__ == "__main__":
    main()
