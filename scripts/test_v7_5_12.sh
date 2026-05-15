#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH="${PYTHONPATH:-$PWD/src}" pytest -q \
  tests/test_dossier_finalization_closeout_export_verify_v7_5_12.py \
  tests/test_dossier_finalization_closeout_export_verify_routes_v7_5_12.py
