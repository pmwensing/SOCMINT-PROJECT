from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
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

    reviewed = release / "V9_8_9_ZIP_REVIEWED_ARTIFACT.md"
    important = release / "V9_8_9_ZIP_IMPORTANT_ARTIFACT.md"
    excluded = release / "V9_8_9_ZIP_EXCLUDED_ARTIFACT.md"
    archived = release / "V9_8_9_ZIP_ARCHIVED_ARTIFACT.md"

    reviewed.write_text("# zip reviewed\n")
    important.write_text("# zip important\n")
    excluded.write_text("# zip excluded\n")
    archived.write_text("# zip archived\n")

    with tempfile.TemporaryDirectory(prefix="socmint-v989-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v989-release-package-zip-smoke")

        paths = {
            "reviewed": "release/V9_8_9_ZIP_REVIEWED_ARTIFACT.md",
            "important": "release/V9_8_9_ZIP_IMPORTANT_ARTIFACT.md",
            "excluded": "release/V9_8_9_ZIP_EXCLUDED_ARTIFACT.md",
            "archived": "release/V9_8_9_ZIP_ARCHIVED_ARTIFACT.md",
        }

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v989-zip-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v989-csrf"

            failures = []

            updates = [
                (paths["reviewed"], True, False, False, "zip reviewed"),
                (paths["important"], False, True, False, "zip important"),
                (paths["archived"], False, True, True, "zip archived"),
            ]

            for path, reviewed_flag, important_flag, archived_flag, note in updates:
                response = client.post(
                    "/api/v1/product/artifacts/review",
                    json={
                        "path": path,
                        "reviewed": reviewed_flag,
                        "important": important_flag,
                        "archived": archived_flag,
                        "note": note,
                    },
                    headers={"X-CSRF-Token": "v989-csrf"},
                )
                ok = response.status_code == 200
                print(("[PASS]" if ok else "[FAIL]"), "seed review", path, response.status_code)
                if not ok:
                    failures.append((f"seed review {path}", response.status_code, response.get_data(as_text=True)[:1000]))

            package_name = "v9_8_9_zip_smoke_package"
            response = client.post(
                "/api/v1/product/release-package/build",
                json={"package_name": package_name, "include_archived": False},
                headers={"X-CSRF-Token": "v989-csrf"},
            )
            package = response.get_json() if response.is_json else {}
            ok = response.status_code == 200 and package.get("version") == "9.8.8"
            print(("[PASS]" if ok else "[FAIL]"), "POST build package", response.status_code)
            if not ok:
                failures.append(("POST build package", response.status_code, response.get_data(as_text=True)[:1500]))

            response = client.post(
                f"/api/v1/product/release-package/{package_name}/zip",
                headers={"X-CSRF-Token": "v989-csrf"},
            )
            zip_result = response.get_json() if response.is_json else {}
            zip_path = Path(zip_result.get("zip_path", ""))
            ok = (
                response.status_code == 200
                and zip_result.get("version") == "9.8.9"
                and zip_path.exists()
                and zip_path.suffix == ".zip"
            )
            print(("[PASS]" if ok else "[FAIL]"), "POST zip package", response.status_code)
            if not ok:
                failures.append(("POST zip package", response.status_code, response.get_data(as_text=True)[:1500]))

            if zip_path.exists():
                with zipfile.ZipFile(zip_path) as zf:
                    entries = set(zf.namelist())

                required_entries = {
                    "PACKAGE_MANIFEST.json",
                    "PACKAGE_INDEX.md",
                    "artifacts/release/V9_8_9_ZIP_REVIEWED_ARTIFACT.md",
                    "artifacts/release/V9_8_9_ZIP_IMPORTANT_ARTIFACT.md",
                }
                forbidden_entries = {
                    "artifacts/release/V9_8_9_ZIP_EXCLUDED_ARTIFACT.md",
                    "artifacts/release/V9_8_9_ZIP_ARCHIVED_ARTIFACT.md",
                }
                has_metadata = any("product_artifact_metadata.json" in item for item in entries)
                has_audit = any("product_artifact_review_audit.json" in item for item in entries)

                ok = (
                    required_entries.issubset(entries)
                    and not forbidden_entries.intersection(entries)
                    and has_metadata
                    and has_audit
                )
                print(("[PASS]" if ok else "[FAIL]"), "zip contains selected package contents")
                if not ok:
                    failures.append(("zip contains selected package contents", 0, json.dumps(sorted(entries), indent=2)[:2500]))

            response = client.get("/api/v1/product/release-packages")
            payload = response.get_json() if response.is_json else {}
            packages = payload.get("packages", [])
            found = any(item.get("package_name") == package_name and item.get("zip_exists") for item in packages)
            ok = response.status_code == 200 and payload.get("version") == "9.8.9" and found
            print(("[PASS]" if ok else "[FAIL]"), "GET package list", response.status_code)
            if not ok:
                failures.append(("GET package list", response.status_code, response.get_data(as_text=True)[:1500]))

            response = client.get(f"/product/release-package/download/{package_name}")
            ok = response.status_code == 200 and response.data[:2] == b"PK"
            print(("[PASS]" if ok else "[FAIL]"), "GET package ZIP download", response.status_code)
            if not ok:
                failures.append(("GET package ZIP download", response.status_code, response.get_data(as_text=True)[:1000]))

            response = client.get("/product/release-package")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Built Packages + ZIP Export" in body and "Release packages JSON" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET release package UI ZIP panel", response.status_code)
            if not ok:
                failures.append(("GET release package UI ZIP panel", response.status_code, body[:1500]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.8.9 product release package ZIP smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
