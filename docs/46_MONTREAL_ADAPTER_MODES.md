# 46 Montreal Street Adapter Modes

## Purpose

The 46 Montreal Street adapter is a case-scoped integration workflow. It does not replace the repository's existing evidence, observation, analytic-claim, audit, entity, timeline, dossier, export, or publication authorities.

The adapter is restricted to canonical case key `46MONST` and operates in one of three modes:

- `off`
- `passive`
- `on`

`passive` is the fail-safe default when no control event exists.

## Control hierarchy

The effective mode is the least permissive of:

1. the system maximum mode;
2. the case adapter mode;
3. the mode requested for one operation.

A case cannot override a restrictive system control, and a one-run request cannot override either persistent control.

## Off

`off` blocks adapter inventory, validation, preview generation, projection and import authorization. Existing authoritative records remain unchanged and preserved.

A transition directly from `off` to `on` is prohibited. The case must enter `passive`, produce a reviewable preview, and then receive a separate approval before `on` can be selected.

## Passive

`passive` may:

- inventory available source material;
- validate metadata, hashes, links and scope;
- prepare deterministic import plans;
- calculate claim-proof projections;
- prepare timeline projections;
- report scope compliance and unresolved contradictions.

`passive` cannot:

- execute an authoritative import;
- assign truth;
- approve claims;
- merge entities;
- mutate a dossier;
- publish or submit evidence;
- trigger public-web collection.

Every passive report must end with:

> No authoritative case records were changed.

## On — controlled import eligibility

`on` does not itself import anything. It makes one separately governed operation eligible: `execute_controlled_import`.

Entering `on` requires:

- explicit operator confirmation;
- an attributable actor;
- an administrative reason;
- a valid approved import-plan SHA-256;
- an existing `passive` state or preview path.

Executing a controlled import requires another explicit confirmation and exact equality with the active import-plan SHA-256. The controller only returns an authorization envelope; it does not write evidence, observations, claims, timelines or dossiers.

## Append-only mode history

System and case mode changes reuse the existing `AuditLog` authority:

- `case_adapter_system_mode_changed`
- `case_adapter_mode_changed`

Mode history is append-only. Disabling the adapter does not delete prior events or imported records.

## 46 Montreal Street scope

The adapter recognizes both the pre-fire proceeding and the post-fire lockout proceeding as distinct case scopes.

For 71 Cowdy Street, the adapter may include only:

- upstairs noise;
- the water leak.

It must exclude all other Cowdy Street issues and must not characterize the Cowdy Street landlord adversely. This restriction is embedded in the adapter scope and included in the deterministic scope hash recorded with mode changes.

## Safety boundary

The following remain prohibited in every adapter mode:

- automatic truth assignment;
- automatic claim approval;
- automatic entity merge;
- automatic dossier mutation;
- publication or filing;
- uncontrolled public-web collection.

These actions require their existing separate repository authorities and human-review gates.
