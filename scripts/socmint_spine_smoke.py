# ruff: noqa: E402
import json
import os
import tempfile

os.environ.setdefault(
    "SOCMINT_SECRET_KEY",
    "dev-secret-key-for-socmint-spine-32chars-plus",
)
os.environ.setdefault("SOCMINT_ADMIN_USER", "admin")
os.environ.setdefault("SOCMINT_ADMIN_PASSWORD", "StrongPass123!")
os.environ.setdefault("SOCMINT_AUTO_CREATE_DB", "1")

from socmint.dashboard import create_app


def main():
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(database_url=f"sqlite:///{tmp}/socmint.db")
        app.config.update(TESTING=True)
        client = app.test_client()

        csrf = "smoke-csrf-token"
        with client.session_transaction() as sess:
            sess["_csrf_token"] = csrf

        login = client.post(
            "/login",
            data={
                "username": "admin",
                "password": "StrongPass123!",
                "csrf_token": csrf,
            },
        )
        assert login.status_code in {200, 302}, login.data

        created = client.post(
            "/api/v1/spine/subjects",
            json={
                "label": "Smoke Subject",
                "seeds": [{"type": "username", "value": "exampleuser"}],
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert created.status_code == 201, created.data
        subject_id = created.get_json()["subject_id"]

        run = client.post(
            f"/api/v1/spine/subjects/{subject_id}/run",
            json={"connectors": ["sherlock", "maigret"]},
            headers={"X-CSRF-Token": csrf},
        )
        assert run.status_code == 202, run.data

        dossier = client.get(f"/api/v1/spine/subjects/{subject_id}/dossier")
        assert dossier.status_code == 200, dossier.data
        body = dossier.get_json()
        assert body["summary"]["connector_runs"] >= 1

        print(json.dumps(body["summary"], indent=2))


if __name__ == "__main__":
    main()
