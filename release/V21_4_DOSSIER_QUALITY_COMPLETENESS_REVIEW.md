# v21.4 Dossier Quality and Completeness Review

Combines section completeness, unresolved citations, narrative coverage, provenance quality, and source readiness into one operator and supervisor review surface.

The review produces explicit blockers, deterministic review identifiers and hashes, section readiness, finding-level provenance scores, and an overall ready or not-ready status.

Routes:

- `GET /dossier-assembly/<case_id>/quality-review?subject_id=<id>`
- `GET /api/v1/dossier-assembly/<case_id>/quality-review?subject_id=<id>`
- `POST /api/v1/dossier-assembly/<case_id>/quality-review-snapshot?subject_id=<id>`

A ready result requires complete substantive sections, narrative coverage, resolved citations, complete provenance, and source readiness. Saving creates an immutable quality review snapshot.

The source package, arrangement history, draft snapshot, and citation snapshot remain unchanged. The existing audit log storage is reused, and no migration is introduced.
