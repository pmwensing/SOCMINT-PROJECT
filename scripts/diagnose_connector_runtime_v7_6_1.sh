#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -f .connector-tools/bin/socmint-connectors-env ]; then
  # shellcheck disable=SC1091
  source .connector-tools/bin/socmint-connectors-env
fi

export PYTHONPATH="$ROOT/src:${PYTHONPATH:-}"

python3 - <<'PY'
from socmint.connector_runtime import connector_runtime_health

payload = connector_runtime_health()
print("SOCMINT Connector Runtime Diagnostic v7.6.1")
print("Summary:", payload["summary"])
print("Schema:", payload["schema"])
print()

native = payload.get("native_dependencies", {})
print("Native dependencies:")
for item in native.get("items", []):
    state = "ok" if item.get("available") else "missing"
    print(f"  {item['name']}: {state} {item.get('path') or ''}")
if not native.get("ready"):
    print("\nNative dependency repair:")
    print(" ", native.get("install_command"))

print("\nConnectors:")
for status in ("ready", "missing", "disabled"):
    items = [item for item in payload["connectors"] if item["status"] == status]
    if not items:
        continue
    print(f"\n{status.upper()}")
    for item in items:
        print(f"  {item['name']}: {item.get('version') or item.get('executable') or 'not detected'}")
        if status != "ready":
            print(f"    install: {item.get('install_command')}")
            print(f"    check:   {item.get('check_command')}")
            hint = item.get("install_hint", {})
            if hint.get("native_dependency_hint"):
                print(f"    native:  {hint['native_dependency_hint']}")
            for step in hint.get("manual_steps", []) or []:
                print(f"    step:    {step}")
PY
