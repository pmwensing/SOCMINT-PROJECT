#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
python3 -m compileall -q src/socmint
pytest -q tests/test_v10_30_case_delivery_registry.py tests/test_v10_30_case_delivery_registry_routes.py
