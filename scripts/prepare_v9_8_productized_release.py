from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    report_path = Path("release/V9_7_PRODUCT_SMOKE_REPORT.json")
    if not report_path.exists():
        print("[!] Run make product-smoke first.")
        return 1

    report = json.loads(report_path.read_text())
    if report.get("status") != "pass":
        print(f"[!] v9.8 blocked. product-smoke status={report.get('status')}")
        return 1

    manifest = {
        "release": "v9.8.0",
        "name": "SOCMINT Workbench v9.8 — Productized Entity Intelligence Platform",
        "generated_at": now_iso(),
        "based_on": "v9.7.1-v9.7.4 product suite",
        "status": "ready_to_tag",
    }

    Path("release/V9_8_PRODUCTIZED_RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    Path("release/V9_8_PRODUCTIZED_RELEASE.md").write_text(
        "# v9.8 Productized Release\n\n"
        "SOCMINT Workbench v9.8 — Productized Entity Intelligence Platform\n\n"
        f"Generated: {manifest['generated_at']}\n\n"
        "Status: ready_to_tag\n"
    )

    print("[+] v9.8 release manifest prepared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
