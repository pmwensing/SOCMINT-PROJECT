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
from socmint.product_artifacts import product_artifacts_manifest  # noqa: E402


def _route_rules(app) -> set[str]:
    return {rule.rule for rule in app.url_map.iter_rules()}


def _routes_containing(app, *needles: str) -> list[str]:
    routes = sorted(_route_rules(app))
    lowered = [needle.lower() for needle in needles]
    return [
        route for route in routes if all(needle in route.lower() for needle in lowered)
    ]


def _get_ok(client, path: str) -> tuple[bool, int, str]:
    response = client.get(path)
    return (
        response.status_code == 200,
        response.status_code,
        response.get_data(as_text=True)[:2500],
    )


def main() -> int:
    manifest = product_artifacts_manifest()
    if manifest.get("status") != "ok" or manifest.get("version") != "10.0.3":
        print("[FAIL] product_artifacts manifest")
        return 1

    with tempfile.TemporaryDirectory(prefix="socmint-v1003-") as tmp:
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/socmint.db"
        os.environ["SOCMINT_DATA_DIR"] = tmp
        os.environ["SOCMINT_CONNECTOR_DRY_RUN"] = "1"
        db.configure_database(os.environ["DATABASE_URL"])

        app = create_app()
        app.config.update(
            TESTING=True, SECRET_KEY="v1003-artifact-pipeline-extraction-smoke"
        )

        with app.test_client() as client:
            with client.session_transaction() as session:
                session["user"] = "v1003-artifact-extraction-smoke"
                session["is_admin"] = True
                session["role"] = "admin"
                session["_csrf_token"] = "v1003-csrf"

            failures: list[tuple[str, int, str]] = []

            response = client.get("/api/v1/product/v10/architecture")
            architecture = response.get_json() if response.is_json else {}
            ok = (
                response.status_code == 200
                and architecture.get("version") == "10.0.0"
                and architecture.get("compatibility", {}).get("missing") == []
                and "product_artifacts.product_artifacts_manifest"
                in architecture.get("foundation", {}).get("extracted_modules", [])
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "v10 architecture includes artifact module",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "v10 architecture includes artifact module",
                        response.status_code,
                        response.get_data(as_text=True)[:4000],
                    )
                )

            # Seed release artifacts so the artifact browser, review, export, and package builders have content.
            release = Path("release")
            release.mkdir(exist_ok=True)
            seeded = {
                "release/V10_0_3_ARTIFACT_SELECTED_REVIEWED.md": "# selected reviewed\n",
                "release/V10_0_3_ARTIFACT_SELECTED_IMPORTANT.md": "# selected important\n",
                "release/V10_0_3_ARTIFACT_EXCLUDED_UNREVIEWED.md": "# excluded unreviewed\n",
                "release/V10_0_3_ARTIFACT_ARCHIVED.md": "# archived\n",
            }
            for path, content in seeded.items():
                Path(path).write_text(content)

            # Verify required route surfaces remain present.
            route_checks = {
                "artifact_browser_ui": ["/product/artifacts"],
                "artifact_browser_api": ["/api/v1/product/artifacts"],
                "artifact_review": _routes_containing(app, "artifact", "review"),
                "artifact_audit": _routes_containing(app, "artifact", "audit"),
                "artifact_export": _routes_containing(app, "artifact", "export"),
                "release_package": _routes_containing(app, "release-package"),
                "release_package_download": _routes_containing(
                    app, "release-package", "download"
                ),
            }

            for key, routes in route_checks.items():
                ok = bool(routes)
                print(
                    ("[PASS]" if ok else "[FAIL]"),
                    f"route surface {key}",
                    ",".join(routes[:5]),
                )
                if not ok:
                    failures.append((f"route surface {key}", 0, "no matching routes"))

            # Exercise artifact browser routes.
            for route in ["/api/v1/product/artifacts", "/product/artifacts"]:
                ok, status, body = _get_ok(client, route)
                print(("[PASS]" if ok else "[FAIL]"), f"GET {route}", status)
                if not ok:
                    failures.append((f"GET {route}", status, body))

            # Try review persistence if the known review endpoint exists.
            if "/api/v1/product/artifacts/review" in _route_rules(app):
                response = client.post(
                    "/api/v1/product/artifacts/review",
                    json={
                        "path": "release/V10_0_3_ARTIFACT_SELECTED_REVIEWED.md",
                        "reviewed": True,
                        "important": True,
                        "archived": False,
                        "note": "v10.0.3 artifact pipeline extraction smoke",
                    },
                    headers={"X-CSRF-Token": "v1003-csrf"},
                )
                ok = response.status_code in {200, 302}
                print(
                    ("[PASS]" if ok else "[FAIL]"),
                    "POST artifact review",
                    response.status_code,
                )
                if not ok:
                    failures.append(
                        (
                            "POST artifact review",
                            response.status_code,
                            response.get_data(as_text=True)[:2500],
                        )
                    )

            for route in ["/api/v1/product/artifact-review-state"]:
                if route in _route_rules(app):
                    ok, status, body = _get_ok(client, route)
                    print(("[PASS]" if ok else "[FAIL]"), f"GET {route}", status)
                    if not ok:
                        failures.append((f"GET {route}", status, body))

            # Exercise all matching JSON/UI surfaces safely.
            candidate_gets = []
            for group in ["artifact_audit", "artifact_export", "release_package"]:
                candidate_gets.extend(route_checks[group])
            post_only_suffixes = (
                "/write",
                "/build",
            )
            for route in sorted(set(candidate_gets)):
                if "{" in route or "<" in route:
                    continue
                if route.endswith(post_only_suffixes):
                    print("[PASS]", f"skip POST-only action route {route}")
                    continue
                ok, status, body = _get_ok(client, route)
                print(("[PASS]" if ok else "[FAIL]"), f"GET {route}", status)
                if not ok:
                    failures.append((f"GET {route}", status, body))

            # Write architecture manifest.
            response = client.post(
                "/api/v1/product/v10/architecture/write",
                headers={"X-CSRF-Token": "v1003-csrf"},
            )
            ok = (
                response.status_code == 200
                and Path("release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.json").exists()
                and Path("release/V10_0_0_PRODUCT_ARCHITECTURE_MANIFEST.md").exists()
            )
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "write v10 architecture manifest",
                response.status_code,
            )
            if not ok:
                failures.append(
                    (
                        "write v10 architecture manifest",
                        response.status_code,
                        response.get_data(as_text=True)[:2500],
                    )
                )

            # Confirm smoke covered the required concepts.
            coverage = {
                "artifacts": bool(route_checks["artifact_browser_api"]),
                "review": bool(route_checks["artifact_review"]),
                "audit": bool(route_checks["artifact_audit"]),
                "export_manifest": bool(route_checks["artifact_export"]),
                "package_builder": bool(route_checks["release_package"]),
                "zip_export": bool(route_checks["release_package_download"]),
            }
            ok = all(coverage.values())
            print(
                ("[PASS]" if ok else "[FAIL]"),
                "artifact pipeline coverage",
                json.dumps(coverage, sort_keys=True),
            )
            if not ok:
                failures.append(
                    ("artifact pipeline coverage", 0, json.dumps(coverage, indent=2))
                )

            if failures:
                for name, status, body in failures:
                    print(f"\n--- FAILURE {name} {status} ---\n{body}")
                return 1

    print("v10.0.3 product artifact pipeline extraction smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
