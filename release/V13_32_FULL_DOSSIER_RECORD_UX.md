# v13.32 — Full Dossier Record UX + Final Operator Polish

## Scope

- Replaces raw lower-section JSON record tables in Full Dossier v2 with collapsible record cards.
- Adds an operator status banner for dossier generated, latest export availability, artifact count, and review state.
- Adds a section review map for fast navigation across dossier sections.
- Adds first-25 record presentation with expand/collapse controls.
- Keeps raw JSON available inside per-record `View raw JSON` disclosure blocks.
- Preserves export payload integrity; only the UI rendering layer changes.

## Acceptance

- Full Dossier v2 renders the latest export panel from v13.31.
- Lower dossier sections render as collapsible cards instead of table rows containing raw JSON blocks.
- Raw JSON remains available for audit/review without mutating the export payload.
- Static regression tests assert operator banner, record cards, section map, controls, and CSS selectors.
