#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
python3 -m compileall -q src/socmint
pytest -q tests/test_v10_32_productization_ux.py tests/test_v10_32_productization_ux_routes.py
