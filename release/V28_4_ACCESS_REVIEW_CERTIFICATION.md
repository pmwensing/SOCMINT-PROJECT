# v28.4 Access Review and Certification

Adds controlled Access Review and Certification workflows for review campaigns, scoped review assignments, certification decisions, expired access findings, excessive access findings, remediation queue generation, closure, and immutable certification history.

Administrators can create a review campaign with a named scope and due date, assign review work to a reviewer for a user or role and optional case, and record one decision per assignment. Supported decisions are certify, revoke, reduce, or defer. Every decision requires an explicit decision reason and binds the review, assignment, reviewer context, retained permissions, event ID, event SHA-256, actor, timestamp, and source IP.

A review cannot close until every assignment has a decision. Duplicate decisions for one assignment are blocked. Revoke and reduce decisions enter a remediation queue with the source decision ID and hash.

The workspace identifies expired access rules when expiry metadata exists and reports excessive access through broad non-administrator roles and broad case-level allow rules.

All write routes require authentication, administrator required authorization, CSRF validation, explicit confirmation, and an administrative reason or decision reason.

review decisions do not directly mutate access policy. Certification is an evidence and governance record; revoke and reduce decisions require a separate v28.2 policy grant, deny, or revocation action. Prior roles, access rules, review events, and decisions remain unchanged.

Routes:

- `GET /administration/access-reviews`
- `GET /api/v1/administration/access-reviews`
- `POST /api/v1/administration/access-reviews`
- `POST /api/v1/administration/access-reviews/<review_id>/assign`
- `POST /api/v1/administration/access-reviews/<review_id>/decide`
- `POST /api/v1/administration/access-reviews/<review_id>/close`

Preservation boundaries:

- immutable certification history
- one decision per review assignment
- prior access-policy records remain unchanged
- `review_decisions_mutate_access_policy: false`
- `remediation_requires_separate_policy_action: true`
- `case_access_scope_changed_by_review: false`
- no connector execution
- no credential or secret exposure

This slice introduces no migration. It uses the existing `audit_logs` table and reads the existing v28.2 access-policy event registry.
