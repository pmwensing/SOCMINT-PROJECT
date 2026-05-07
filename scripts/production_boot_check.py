#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.socmint.dashboard import create_app  # noqa: E402
from src.socmint.main import generate_secrets  # noqa: E402


def configure_env(root):
    values = generate_secrets()
    values.update(
        {
            "SOCMINT_ADMIN_USER": "admin",
            "SOCMINT_ALLOW_SIGNUP": "false",
            "SOCMINT_AUTO_CREATE_DB": "false",
            "SOCMINT_DATA_DIR": str(root),
            "DATABASE_URL": f"sqlite:///{root / 'socmint.db'}",
        }
    )
    os.environ.update(values)
    return values


def run_local_check():
    with tempfile.TemporaryDirectory(prefix="socmint-prod-smoke-") as temp_dir:
        root = Path(temp_dir)
        configure_env(root)
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            check=True,
        )
        app = create_app()
        app.config.update(TESTING=True)
        with app.test_client() as client:
            health = client.get("/healthz")
            login = client.get("/login")
        if health.status_code != 200 or login.status_code != 200:
            raise SystemExit("local production boot check failed")
    print("Local production boot check passed")


def run_docker_config_check():
    env = os.environ.copy()
    env["SOCMINT_ENV_FILE"] = ".env.example"
    subprocess.run(
        ["docker", "compose", "--env-file", ".env.example", "config"],
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            ".env.example",
            "--profile",
            "postgres",
            "config",
        ],
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
    )
    print("Docker Compose production config check passed")


def main():
    run_local_check()
    run_docker_config_check()


if __name__ == "__main__":
    main()
