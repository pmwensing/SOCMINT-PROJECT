#!/usr/bin/env bash
set -euo pipefail

echo "[+] Container connector CLI enabled smoke"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for container connector CLI smoke" >&2
  exit 1
fi

if ! docker compose ps app >/dev/null 2>&1; then
  echo "docker compose app service is not available. Rebuild first:" >&2
  echo "SOCMINT_INSTALL_CONNECTORS=true SOCMINT_CONNECTOR_MODE=real SOCMINT_AUTHORIZED_REALWORLD_CONNECTORS=true docker compose --profile worker up -d --build" >&2
  exit 1
fi

docker compose exec -T app python - <<'PY'
import json
import shutil
import subprocess

checks = []
commands = {
    "holehe": ["holehe", "--help"],
    "h8mail": ["h8mail", "--help"],
    "socialscan": ["socialscan", "--help"],
    "sherlock": ["sherlock", "--help"],
    "maigret": ["python", "-m", "maigret", "--version"],
}

for name, command in commands.items():
    executable = shutil.which(command[0])
    if executable is None and command[:3] == ["python", "-m", "maigret"]:
        executable = shutil.which("python") or shutil.which("python3")
    row = {"name": name, "command": command, "executable": executable, "ready": bool(executable)}
    if executable:
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=20)
            row["returncode"] = result.returncode
            row["stdout_head"] = result.stdout[:400]
            row["stderr_head"] = result.stderr[:400]
            row["invokable"] = result.returncode in {0, 1, 2}
        except Exception as exc:
            row["invokable"] = False
            row["error"] = str(exc)
    else:
        row["invokable"] = False
    checks.append(row)

print(json.dumps({"schema": "socmint.connector_cli_container.v12_10_1", "checks": checks}, indent=2))
missing = [row["name"] for row in checks if not row.get("ready")]
not_invokable = [row["name"] for row in checks if not row.get("invokable")]
assert not missing, f"Missing connector CLIs in container: {missing}"
assert not not_invokable, f"Connector CLIs not invokable in container: {not_invokable}"
print("PASS container connector CLI enabled smoke")
PY
