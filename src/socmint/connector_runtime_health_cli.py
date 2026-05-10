from __future__ import annotations

import argparse
import json
from collections import defaultdict

from .connector_runtime import connector_runtime_health


def _print_human(payload: dict) -> None:
    summary = payload.get("summary", {})
    print("SOCMINT Connector Runtime Health")
    print(f"Schema: {payload.get('schema')}")
    print(
        "Summary: "
        f"ready={summary.get('ready', 0)} "
        f"missing={summary.get('missing', 0)} "
        f"disabled={summary.get('disabled', 0)} "
        f"dry_run_forced={payload.get('dry_run_forced')}"
    )

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in payload.get("connectors", []):
        grouped[item.get("status", "unknown")].append(item)

    for status in ("ready", "missing", "disabled", "unknown"):
        items = grouped.get(status, [])
        if not items:
            continue
        print(f"\n{status.upper()} ({len(items)})")
        for item in items:
            print(f"- {item['name']}")
            print(f"  version/path: {item.get('version') or item.get('executable') or 'not detected'}")
            print(f"  target types: {', '.join(item.get('target_types', []))}")
            print(f"  sample: {' '.join(item.get('sample_command', []))}")
            if status != "ready":
                print(f"  install: {item.get('install_command')}")
                print(f"  check:   {item.get('check_command')}")
            note = item.get("notes") or item.get("install_hint", {}).get("runtime_note")
            if note:
                print(f"  note:    {note}")

    missing = grouped.get("missing", [])
    if missing:
        print("\nRepair quick-start:")
        print("  make install-connectors")
        print("  source .connector-tools/bin/socmint-connectors-env")
        print("  make connectors-health")
        heavy = [item for item in missing if item["name"] in {"maigret", "archivebox"}]
        if heavy:
            print("\nNative dependency hint for Maigret/ArchiveBox/pycairo failures:")
            print("  sudo apt update")
            print("  sudo apt install -y pkg-config cmake build-essential python3-dev libcairo2-dev libgirepository-2.0-dev gir1.2-gtk-3.0")
        if any(item["name"] == "phoneinfoga" for item in missing):
            print("\nPhoneInfoga hint:")
            print("  Install the official PhoneInfoga Linux binary and place it at .connector-tools/bin/phoneinfoga")
            print("  chmod +x .connector-tools/bin/phoneinfoga")


def main() -> None:
    parser = argparse.ArgumentParser(description="SOCMINT connector runtime health")
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    args = parser.parse_args()
    payload = connector_runtime_health()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _print_human(payload)


if __name__ == "__main__":
    main()
