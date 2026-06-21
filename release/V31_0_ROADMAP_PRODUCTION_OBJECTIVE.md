# v31.0 — Operational Analytic Workflow and Dossier Publication

## Program objective

Move explicitly approved v30 dossier contributions through a controlled publication workflow that separates draft assembly, editorial validation, human release approval, immutable publication, and later supersession.

## Primary workspace

**Publication Review Workspace**

v31.0 implements a read-only inventory of approved v30 contributions, existing dossier assembly and export contracts, draft/published revision state, release blockers, and publication readiness.

## Workflow spine

```text
approved dossier contribution
→ publication candidate
→ draft dossier revision
→ editorial validation
→ human release approval
→ immutable published revision
→ supersession and revision history
```

## Roadmap

| Slice | Title | Purpose | Status |
|---|---|---|---|
| v31.0 | Publication Review Workspace | Inventory publication inputs, existing dossier contracts, and readiness blockers. | Implemented |
| v31.1 | Publication Candidate Contract | Create append-only candidates from approved v30 contributions. | Next |
| v31.2 | Draft Dossier Revision Assembly | Assemble deterministic draft revisions without publishing them. | Planned |
| v31.3 | Editorial Validation and Policy Gate | Validate completeness, provenance, conflicts, policy, and release blockers. | Planned |
| v31.4 | Human Release Approval | Require explicit release approval before publication. | Planned |
| v31.5 | Immutable Published Revision | Create immutable published revisions with deterministic bindings. | Planned |
| v31.6 | Supersession and Revision History | Preserve prior revisions while allowing controlled replacement. | Planned |
| v31.7 | Product Review and Browser E2E | Validate the complete workflow and close v31. | Planned |

## Implemented boundaries

- the Publication Review Workspace is read-only;
- only approved v30 dossier-contribution decisions are publication inputs;
- existing dossier assembly, export, and release contracts remain authoritative;
- draft and published release records are inventoried without mutation;
- no automatic publication or release approval is available;
- no database migration was introduced.

## Validation contract

```bash
python3 -m pytest -q tests/test_v31_0*.py
python3 -m pytest -q tests/test_v31*.py
python3 -m pytest -q
python3 -m ruff check src tests scripts
```

The next action is `implement_v31_1_publication_candidate_contract`.
