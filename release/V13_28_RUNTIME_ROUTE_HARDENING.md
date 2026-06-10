# v13.28 - Runtime Route Hardening

## Purpose

Harden runtime route behavior around latest full-report export lookup and normalization review queue rendering.

## Added

- Safe latest full-report export lookup when the dossier root is unavailable.
- Template guard coverage so normalization review queue rendering uses the payload `items` key instead of colliding with dictionary methods.

## Verification

- `tests/test_v13_28_runtime_route_hardening.py`

## Value

Runtime UI paths remain stable when export storage is unavailable and review queue payloads render the intended item collection.
