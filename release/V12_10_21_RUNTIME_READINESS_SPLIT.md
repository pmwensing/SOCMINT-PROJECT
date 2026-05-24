# SOCMINT v12.10.21 — Runtime Readiness Diagnostic Split + Tor Nonblocking Dashboard Policy

## Added

- `/api/v1/release/runtime`
- `/release/runtime`
- `src/socmint/release_runtime_readiness_v12_10_21.py`
- `src/socmint/release_runtime_routes_v12_10_21.py`
- `src/socmint/templates/release_runtime.html`
- `scripts/release_runtime_readiness_gate_v12_10_21.py`

## Policy

`/release/status` may return `GO` when local runtime readiness passes, even when Tor hidden-service file visibility is unavailable inside the app container.

Tor hidden-service checks are now informational unless onion publishing is explicitly required by a later operator policy.

## GO criteria

- release manifest matches
- required files are present
- latest passing release gate exists
- local `/readyz` works
- local dashboard HTTP works

## Verify

```bash
python3 scripts/release_runtime_readiness_gate_v12_10_21.py
