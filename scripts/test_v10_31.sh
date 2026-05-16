#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
python3 -m compileall -q src/socmint
pytest -q tests/test_v10_31_human_approval_gate.py tests/test_v10_31_human_approval_gate_routes.py
