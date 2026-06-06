from __future__ import annotations

import json

from src.socmint.export_blocker_demo_v13_40 import create_export_blocker_demo


def main() -> None:
    print(json.dumps(create_export_blocker_demo(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
