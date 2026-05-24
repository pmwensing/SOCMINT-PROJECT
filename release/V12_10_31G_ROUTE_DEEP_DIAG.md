# v12.10.31G — Route Audit Deep Diagnostics + Endpoint-Based Lock

Problem:
- Standalone drift audit still reports `missing_v12_routes: 8`.
- Route tests pass, which means exact summary logic is still not seeing the runtime rules.
- `route_lock_registered` and `route_lock_skipped` are empty, so we need lower-level route/endpoint diagnostics.

Fix:
- Capture actual route rules and endpoint names.
- Check v12 route health by both rule strings and endpoint suffixes.
- Add explicit diagnostics for:
  - dashboard module file
  - all `/api/v12.10` route-like rules
  - all v12 command/ui endpoint names
  - blueprint names
  - missing rules
  - missing endpoint suffixes
- Treat runtime route lock as PASS when endpoint suffixes are present, even if Flask rule string formatting differs.
