#!/usr/bin/env bash
set -euo pipefail

echo "[+] Connector CLI enabled smoke"

python3 - <<'PY'
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

print(json.dumps({"schema": "socmint.connector_cli_enabled.v12_10_1", "checks": checks}, indent=2))
missing = [row["name"] for row in checks if not row.get("ready")]
not_invokable = [row["name"] for row in checks if not row.get("invokable")]
assert not missing, f"Missing connector CLIs: {missing}"
assert not not_invokable, f"Connector CLIs not invokable: {not_invokable}"
print("PASS connector CLI enabled smoke")
PY
