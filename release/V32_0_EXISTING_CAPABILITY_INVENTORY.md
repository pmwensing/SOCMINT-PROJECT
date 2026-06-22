# v32.0 — Existing Capability Inventory

v32 coordinates existing publication and distribution capabilities. It does not replace them.

## v31 publication capabilities to reuse

- `publication_candidate_v31_1.py` — controlled publication candidate history
- `draft_dossier_revision_v31_2.py` — deterministic draft revision assembly
- `editorial_validation_v31_3.py` — editorial and policy validation
- `human_release_approval_v31_4.py` — explicit human release decision
- `immutable_published_revision_v31_5.py` — sealed published revision
- `publication_supersession_v31_6.py` — immutable supersession history

The immutable v31.5 published revision is the only valid source object for a v32 dissemination package.

## v22 distribution capabilities to reuse

- `dossier_release_workspace_v22_0.py`
- `dossier_release_authorization_v22_1.py`
- `dossier_release_preview_v22_2.py`
- `dossier_secure_distribution_v22_3.py`
- `dossier_delivery_receipt_v22_4.py`
- `dossier_release_history_v22_6.py`

Related delivery, recall, reissue, and ledger routes already in the repository must be inventoried before any new v32 runtime contract is introduced.

## Gaps v32 is intended to close

1. Bind immutable published revisions to explicit audience and recipient contracts.
2. Assemble deterministic dissemination packages without rewriting the publication.
3. Place human authorization and policy review directly before dissemination.
4. Unify delivery attempts, receipts, failures, feedback, corrections, recall, and retention into one governance history.
5. Make the full lifecycle visible in a dedicated operator workspace.

## Explicit non-goals

- no second publication system;
- no replacement delivery engine;
- no automatic recipient authorization;
- no automatic external transmission;
- no mutation or deletion of published or delivery history;
- no new connector family without a proven capability gap;
- no schema migration during the planning entry gate.
