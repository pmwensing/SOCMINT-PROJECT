#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from socmint.v12_10_54_runtime_guard import assert_real_db_upgrade_allowed


def main() -> int:
    result = assert_real_db_upgrade_allowed()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
