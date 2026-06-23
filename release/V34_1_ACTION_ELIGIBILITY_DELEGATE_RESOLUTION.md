# v34.1 — Action Eligibility and Delegate Resolution

## Objective

Add a deterministic, case-scoped, read-only resolution layer between the v33 action queue and future v34 confirmation forms.

The layer determines whether each queued action is eligible to proceed to confirmation and identifies exactly one authoritative v32 delegate service. It does not invoke that service.

## Inputs

- canonical v33.2 case action queue
- queue action name, stage, priority, severity, delegate service, targets, and confirmation flags
- fixed v34 delegate registry for the eight currently supported governance actions

## Eligibility checks

Each action is blocked unless all applicable checks pass:

- the action is registered for v34 execution
- the queue delegate exactly matches the authoritative registry
- every required target identifier is present
- explicit confirmation is required
- automatic execution is disabled

## Output

For each queue item, v34.1 returns:

- eligibility status
- authoritative delegate module and function
- required and missing targets
- explicit eligibility blockers
- deterministic resolution identifier and SHA-256 digest
- confirmation and automatic-execution constraints

The aggregate response includes eligible and blocked counts, the next eligible action, and a deterministic summary hash.

## Route

`GET /api/v1/dissemination-governance/cases/<case_id>/action-eligibility`

The route is administrator-only and read-only.

## Preserved boundaries

- no service invocation
- no form submission or confirmation acceptance
- no automatic execution
- no direct transport logic
- no source-record mutation
- no duplicate governance persistence
- no secret or endpoint rendering
- v32 services remain authoritative
- the v33 action queue remains the source read model

## Next action

`implement_v34_2_human_confirmation_form_framework`
