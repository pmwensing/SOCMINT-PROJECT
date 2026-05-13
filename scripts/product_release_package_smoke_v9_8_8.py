from __future__ import annotations

import json
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

    reviewed = release / "V9_8_8_PACKAGE_REVIEWED_ARTIFACT.md"
    important = release / "V9_8_8_PACKAGE_IMPORTANT_ARTIFACT.md"
    excluded = release / "V9_8_8_PACKAGE_EXCLUDED_ARTIFACT.md"
    archived = release / "V9_8_8_PACKAGE_ARCHIVED_ARTIFACT.md"

    reviewed.write_text("# package reviewed\n")
    important.write_text("# package important\n")
    excluded.write_text("# package excluded\n")
    archived.write_text("# package archived\n")

    with tempfile.TemporaryDirectory(prefix="socmint-v988-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="v988-release-package-smoke")

        paths = {
            "reviewed": "release/V9_8_8_PACKAGE_REVIEWED_ARTIFACT.md",
            "important": "release/V9_8_8_PACKAGE_IMPORTANT_ARTIFACT.md",
            "excluded": "release/V9_8_8_PACKAGE_EXCLUDED_ARTIFACT.md",
            "archived": "release/V9_8_8_PACKAGE_ARCHIVED_ARTIFACT.md",
        }

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v988-package-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v988-csrf"

            failures = []

            updates = [
                (paths["reviewed"], True, False, False, "package reviewed"),
                (paths["important"], False, True, False, "package important"),
                (paths["archived"], False, True, True, "package archived"),
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
                    headers={"X-CSRF-Token": "v988-csrf"},
                )
                ok = response.status_code == 200
                print(("[PASS]" if ok else "[FAIL]"), "seed review", path, response.status_code)
                if not ok:
                    failures.append((f"seed review {path}", response.status_code, response.get_data(as_text=True)[:1000]))

            response = client.get("/api/v1/product/release-package")
            preview = response.get_json() if response.is_json else {}
            preview_paths = {item.get("path") for item in preview.get("selected_artifacts", [])}
            ok = (
                response.status_code == 200
                and preview.get("version") == "9.8.8"
                and paths["reviewed"] in preview_paths
                and paths["important"] in preview_paths
                and paths["excluded"] not in preview_paths
                and paths["archived"] not in preview_paths
            )
            print(("[PASS]" if ok else "[FAIL]"), "GET release package preview", response.status_code)
            if not ok:
                failures.append(("GET release package preview", response.status_code, response.get_data(as_text=True)[:1500]))

            package_name = "v9_8_8_smoke_package"
            response = client.post(
                "/api/v1/product/release-package/build",
                json={"package_name": package_name, "include_archived": False},
                headers={"X-CSRF-Token": "v988-csrf"},
            )
            package = response.get_json() if response.is_json else {}
            package_root = Path(package.get("package_path", ""))
            ok = (
                response.status_code == 200
                and package.get("version") == "9.8.8"
                and package_root.exists()
                and (package_root / "PACKAGE_MANIFEST.json").exists()
                and (package_root / "PACKAGE_INDEX.md").exists()
            )
            print(("[PASS]" if ok else "[FAIL]"), "POST build release package", response.status_code)
            if not ok:
                failures.append(("POST build release package", response.status_code, response.get_data(as_text=True)[:1500]))

            if package_root.exists():
                manifest = json.loads((package_root / "PACKAGE_MANIFEST.json").read_text())
                copied_sources = {item.get("source") for item in manifest.get("copied_artifacts", [])}
                ok = (
                    paths["reviewed"] in copied_sources
                    and paths["important"] in copied_sources
                    and paths["excluded"] not in copied_sources
                    and paths["archived"] not in copied_sources
                    and manifest.get("metadata_file_count", 0) >= 2
                )
                print(("[PASS]" if ok else "[FAIL]"), "package contents selected only")
                if not ok:
                    failures.append(("package contents selected only", 0, json.dumps(manifest, indent=2)[:2000]))

            response = client.get("/product/release-package")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Product Release Package Builder" in body and paths["reviewed"] in body
            print(("[PASS]" if ok else "[FAIL]"), "GET release package UI", response.status_code)
            if not ok:
                failures.append(("GET release package UI", response.status_code, body[:1500]))

            response = client.get("/product/artifacts")
            body = response.get_data(as_text=True)
            ok = response.status_code == 200 and "Release Package Builder" in body and "/product/release-package" in body
            print(("[PASS]" if ok else "[FAIL]"), "GET artifacts package panel", response.status_code)
            if not ok:
                failures.append(("GET artifacts package panel", response.status_code, body[:1500]))

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v9.8.8 product release package smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
