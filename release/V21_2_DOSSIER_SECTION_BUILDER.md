# v21.2 Dossier Section Builder

Builds a structured draft dossier from the latest saved v21 arrangement and the currently imported v20 findings package.

The builder provides:

- ordered dossier sections
- explicit finding order within each section
- section narratives
- section-level completeness checks
- deterministic draft ids and SHA-256 hashes
- immutable draft snapshots

Section completeness evaluates narrative presence, assigned findings, evidence references, claim citations, and source context. Empty structural sections do not reduce completeness; only sections containing findings are treated as substantive.

Routes:

- `GET /api/v1/dossier-assembly/<case_id>/draft`
- `POST /api/v1/dossier-assembly/<case_id>/draft-snapshot`

The draft is blocked until a saved arrangement and current verified package import exist. Snapshot events preserve the source package id, manifest hash, import record, arrangement record, arrangement hash, ordered sections, and completeness result.

The imported package and arrangement history remain unchanged. The existing `audit_logs` table is reused, and no migration is introduced.

The workspace UI exposes deterministic draft output, section-level completeness, finding-order controls, and immutable snapshot creation.
