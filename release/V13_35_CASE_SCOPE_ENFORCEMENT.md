# v13.35 - Case Scope Enforcement

## Scope

This build starts the explicit case/scope enforcement track from the updated product build spec.

## Included

- Optional `case_key` binding on spine subjects
- Case-filtered spine subject listing
- Case-scope validation for new spine seeds
- Subject-scope validation for connector runs that reference a seed
- Migration `0015_spine_subject_case_scope`
- Regression tests for case filtering, mismatched case rejection, cross-subject seed rejection, and matching case/seed acceptance

## Operator Result

New subject intelligence can be bound to an explicit case key, and connector runs can no longer accidentally pair one subject with another subject's seed.
