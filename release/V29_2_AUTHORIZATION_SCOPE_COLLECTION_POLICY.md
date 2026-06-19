# v29.2 Authorization, Scope, and Collection Policy

Adds controlled collection-policy records and evaluation before a v29.1 job can enter the authorized state.

Policies define permitted source classes, collection purpose, jurisdiction metadata, case, entity, and source scope, deny rules, exclusions, validity dates, expiry, and review dates.

Policy revisions create new immutable versions. Prior definitions and evaluations remain unchanged.

Evaluation compares the collection-job contract with active policy records. Source class, purpose, jurisdiction, case scope, entity scope, source scope, deny rules, exclusions, validity, and expiry are evaluated. deny overrides allow.

An allowing evaluation produces a signed evaluation reference for the v29.1 authorization transition. A denied evaluation cannot authorize or queue the job.

The workspace reports active and superseded policies, expired and review-due policies, decision counts, missing metadata findings, and immutable policy history.

All writes require administrator required access, CSRF validation, explicit confirmation, and an administrative or evaluation reason.

Preservation boundaries:

- policy evaluation before authorization
- immutable policy history
- no connector execution
- no job mutation during evaluation
- no case-access change
- no evidence rewrite
- no secret exposure

Routes:

- `GET /collection-operations/policies`
- `GET /api/v1/collection-operations/policies`
- `POST /api/v1/collection-operations/policies`
- `POST /api/v1/collection-operations/policies/<policy_id>/revise`
- `POST /api/v1/collection-operations/jobs/<collection_job_id>/evaluate-policy`

This slice introduces no migration.
