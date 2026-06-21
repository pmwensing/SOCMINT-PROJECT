from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from socmint import database as db  # noqa: E402
from socmint.dashboard import create_app  # noqa: E402


def main() -> int:
    release = ROOT / "release"
    release.mkdir(exist_ok=True)

    selected_reviewed = release / "V9_8_7_SELECTED_REVIEWED_ARTIFACT.md"
    selected_important = release / "V9_8_7_SELECTED_IMPORTANT_ARTIFACT.md"
    excluded = release / "V9_8_7_EXCLUDED_UNREVIEWED_ARTIFACT.md"
    archived = release / "V9_8_7_ARCHIVED_IMPORTANT_ARTIFACT.md"

    selected_reviewed.write_text("# reviewed selected\n")
    selected_important.write_text("# important selected\n")
    excluded.write_text("# excluded unreviewed\n")
    archived.write_text("# archived important\n")

    with tempfile.TemporaryDirectory(prefix="socmint-v987-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v987-export-manifest-smoke")

        paths = {
            "reviewed": "release/V9_8_7_SELECTED_REVIEWED_ARTIFACT.md",
            "important": "release/V9_8_7_SELECTED_IMPORTANT_ARTIFACT.md",
            "excluded": "release/V9_8_7_EXCLUDED_UNREVIEWED_ARTIFACT.md",
            "archived": "release/V9_8_7_ARCHIVED_IMPORTANT_ARTIFACT.md",
        }

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v987-export-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v987-csrf"

            failures = []

            updates = [
                (paths["reviewed"], True, False, False, "reviewed artifact"),
                (paths["important"], False, True, False, "important artifact"),
                (paths["archived"], False, True, True, "archived important artifact"),
            ]

            for path, reviewed, important, archived_flag, note in updates:
                response = client.post(
                    "/api/v1/product/artifacts/review",
                    json={
                        "path": path,
                        "reviewed": reviewed,
                        "important": important,
                        "archived": archived_flag,
                        "note": note,
                    },
                    headers={"X-CSRF-Token": "v987-csrf"},
                )
                ok = response.status_code == 200 and response.is_json
                print(
                    ("[PASS]" if ok else "[FAIL]"),
                    "seed review",
                    path,
                    response.status_code,
                )
                if not ok:
                    failures.append(
                        (
                            f"seed review {path}",
                            response.status_code,
                            response.get_data(as_text=True)[:1000],
                        )
                    )

            response = client.get("/api/v1/product/artifact-export-manifest")
            payload = response.get_json() if response.is_json else {}
            manifest_paths = {item.get("path") for item in payload.get("artifacts", [])}

            ok = (
                response.status_code == 200
                and payload.get("version") == "9.8.7"
                and paths["reviewed"] in manifest_paths
                and paths["important"] in manifest_paths
                and paths["excluded"] not in manifest_paths
                and paths["archived"] not in manifest_paths
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET manifest selected active artifacts",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET manifest selected active artifacts",
                        response.status_code,
                        response.get_data(as_text=True)[:1500],
                    )
                )

            response = client.get(
                "/api/v1/product/artifact-export-manifest?include_archived=true"
            )
            payload_with_archived = response.get_json() if response.is_json else {}
            manifest_paths_archived = {
                item.get("path") for item in payload_with_archived.get("artifacts", [])
            }
            ok = (
                response.status_code == 200
                and paths["archived"] in manifest_paths_archived
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET manifest include archived",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET manifest include archived",
                        response.status_code,
                        response.get_data(as_text=True)[:1500],
                    )
                )

            response = client.post(
                "/api/v1/product/artifact-export-manifest/write",
                json={"include_archived": False},
                headers={"X-CSRF-Token": "v987-csrf"},
            )
            payload = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and Path(
                    "release/V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.json"
                ).exists()
                and Path("release/V9_8_7_PRODUCT_ARTIFACT_EXPORT_MANIFEST.md").exists()
                and payload.get("artifacts_written", {}).get("json")
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "POST write manifest",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "POST write manifest",
                        response.status_code,
                        response.get_data(as_text=True)[:1500],
                    )
                )

            response = client.get("/product/artifacts/export-manifest")
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Product Artifact Export Manifest" in body
                and paths["reviewed"] in body
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET export manifest UI",
                response.status_code,
            )
            if not ok:
                failures.append(
                    ("GET export manifest UI", response.status_code, body[:1500])
                )

            response = client.get("/product/artifacts")
            body = response.get_data(as_text=True)
            ok = (
                response.status_code == 200
                and "Export Manifest" in body
                and "artifact-export-manifest" in body
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "GET artifact browser export panel",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "GET artifact browser export panel",
                        response.status_code,
                        body[:1500],
                    )
                )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.8.7 product artifact export manifest smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
