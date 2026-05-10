from __future__ import annotations

import json

from .connector_runtime import connector_runtime_health


def main() -> None:
    print(json.dumps(connector_runtime_health(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
