# SOCMINT v12.10.20 — Release Dashboard Container Mount Contract + Self-Healing Operator Fix

Adds `/api/v1/release/mounts` and `/release/mounts`.

The mount contract checks whether the app container can see release dashboard files, scripts, and gate report directories.

Required visible paths:

- `release/CURRENT_STATUS.json`
- `release/*.md`
- `scripts/release_dashboard_decision_gate_v12_10_19.py`
- `var/socmint/rc_reports`

Run:

`python3 scripts/release_mount_contract_gate_v12_10_20.py`
