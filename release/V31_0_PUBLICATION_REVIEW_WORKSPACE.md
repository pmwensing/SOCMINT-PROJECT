# v31 — Publication Workflow

Implemented slices: v31.0 through v31.7.

The production WSGI application registers the complete publication route chain exactly once. Final GitHub checks are running on the current head.

The only remaining closure gate is the browser E2E rerun against the final production-wiring head.
