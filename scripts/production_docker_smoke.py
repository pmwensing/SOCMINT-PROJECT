#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.socmint.main import generate_secrets  # noqa: E402


def write_env_file(path):
    values = generate_secrets()
    admin_password = values["SOCMINT_SECRET_KEY"][:24] + "Aa1!"
    values.update(
        {
            "SOCMINT_ADMIN_USER": "admin",
            "SOCMINT_ADMIN_PASSWORD": admin_password,
            "SOCMINT_ALLOW_SIGNUP": "false",
            "SOCMINT_AUTO_CREATE_DB": "false",
            "SOCMINT_BACKUP_PASSPHRASE": values["SOCMINT_BACKUP_PASSPHRASE"],
            "SOCMINT_DATA_DIR": "/var/lib/socmint",
            "SOCMINT_HTTPS": "false",
            "DATABASE_URL": "sqlite:////var/lib/socmint/socmint.db",
            "POSTGRES_DB": "socmint",
            "POSTGRES_PASSWORD": values["SOCMINT_BACKUP_PASSPHRASE"][:24] + "Aa1!",
            "POSTGRES_USER": "socmint",
        }
    )
    lines = [f"{key}={value}" for key, value in sorted(values.items())]
    path.write_text("\n".join(lines) + "\n")
    return {"admin_user": "admin", "admin_password": admin_password}


def compose_command(env_file, *args):
    env = os.environ.copy()
    env["SOCMINT_ENV_FILE"] = str(env_file)
    return subprocess.run(
        ["docker", "compose", "--project-name", "socmint-smoke", *args],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
    )


def compose_check(env_file, *args):
    env = os.environ.copy()
    env["SOCMINT_ENV_FILE"] = str(env_file)
    return subprocess.run(
        ["docker", "compose", "--project-name", "socmint-smoke", *args],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_app(env_file, timeout_seconds=90):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = compose_check(
            env_file,
            "exec",
            "-T",
            "app",
            "python",
            "-c",
            (
                "import urllib.request; "
                "urllib.request.urlopen('http://127.0.0.1:5000/readyz', timeout=2)"
            ),
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError("app container did not become healthy")


def wait_for_tor_hostname(env_file, timeout_seconds=90):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = compose_check(
            env_file,
            "exec",
            "-T",
            "tor",
            "test",
            "-s",
            "/var/lib/tor/socmint/hostname",
        )
        if result.returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError("tor hidden service hostname was not created")


def run_app_python(env_file, code, *extra_args):
    return compose_command(
        env_file,
        "exec",
        "-T",
        "app",
        "python",
        "-c",
        code,
        *extra_args,
    )


def exercise_dashboard(env_file, credentials):
    code = r"""
import re
import sys
from src.socmint.dashboard import create_app

username, password = sys.argv[1], sys.argv[2]
app = create_app()
app.config.update(TESTING=True)
client = app.test_client()

ready = client.get("/readyz")
assert ready.status_code == 200, ready.status_code
assert ready.headers.get("X-Request-ID")

login_page = client.get("/login")
token = re.search(rb'name="csrf_token" value="([^"]+)"', login_page.data).group(1)
login = client.post(
    "/login",
    data={"username": username, "password": password, "csrf_token": token.decode()},
)
assert login.status_code == 302, login.status_code

dashboard = client.get("/")
assert dashboard.status_code == 200, dashboard.status_code

run_page = client.get("/")
token = re.search(rb'name="csrf_token" value="([^"]+)"', run_page.data).group(1)
queued = client.post(
    "/target/run",
    data={
        "target": "rehearsal-user",
        "tools": "",
        "enrich": "",
        "csrf_token": token.decode(),
    },
)
assert queued.status_code == 302, queued.status_code

jobs = client.get("/jobs")
assert jobs.status_code == 200, jobs.status_code
assert b"rehearsal-user" in jobs.data
"""
    run_app_python(
        env_file,
        code,
        credentials["admin_user"],
        credentials["admin_password"],
    )


def process_and_verify_job(env_file):
    compose_command(env_file, "up", "-d", "worker")
    code = r"""
import time
from src.socmint import database as db
from src.socmint.config import load_settings

db.configure_database(load_settings(require_secret=False).database_url)
deadline = time.monotonic() + 60
while time.monotonic() < deadline:
    jobs = db.list_scan_jobs(limit=5)
    if (
        jobs
        and jobs[0].target_value == "rehearsal-user"
        and jobs[0].status == "completed"
        and db.get_dossier("rehearsal-user") is not None
    ):
        break
    time.sleep(2)
else:
    jobs = db.list_scan_jobs(limit=5)
    status = jobs[0].status if jobs else "missing"
    raise AssertionError(f"queued worker job did not complete: {status}")
"""
    run_app_python(env_file, code)


def main():
    with tempfile.TemporaryDirectory(prefix="socmint-docker-smoke-") as temp_dir:
        env_file = Path(temp_dir) / "socmint.env"
        credentials = write_env_file(env_file)
        try:
            compose_command(env_file, "up", "--build", "-d", "app", "tor")
            wait_for_app(env_file)
            wait_for_tor_hostname(env_file)
            exercise_dashboard(env_file, credentials)
            process_and_verify_job(env_file)
        finally:
            compose_command(env_file, "down", "-v")
    print("Docker production deployment rehearsal passed")


if __name__ == "__main__":
    main()
