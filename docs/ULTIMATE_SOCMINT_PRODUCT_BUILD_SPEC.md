# Ultimate SOCMINT + Dossier Product Build Spec

This is the end-state build spec for a production-ready SOCMINT and dossier
platform. It is written as an implementation blueprint, not just a vision doc.

## 1. Product Boundary

Build a secure, evidence-first SOCMINT workbench for authorized investigations.

Allowed product goals:

- Private Tor hidden-service access.
- Secure hosting, metadata minimization, encrypted backups, and strong audit.
- Responsible rate limiting and quotas.
- Public/open-source intelligence collection through approved connectors.
- Evidence capture, hashing, chain of custody, analyst review, and export.
- Free and paid memberships with feature and usage limits.

Out of scope:

- Credential theft, bypass, evasion, anti-detection, or private-data access.
- Circumventing platform controls or collecting login-gated data without
  explicit authorization.
- Paid tiers that bypass responsible-use scope or legal/ethical gates.

Target rating after implementation:

- Product vision: 8.5+/10
- Engineering specificity: 8.5+/10
- Safety/compliance framing: 8.5+/10
- Commercial packaging: 8.5+/10
- Release readiness: 8.5+/10

## 2. Primary User Journeys

### Free Evaluation

1. User signs up.
2. User accepts responsible-use terms.
3. System assigns the `free` plan.
4. User creates one case and one subject.
5. User runs limited connectors.
6. User sees account discoveries and assertions as reviewable leads.
7. User exports a watermarked HTML/JSON dossier.
8. Upgrade prompts explain the exact capability or quota needed.

### Pro Analyst

1. User creates case and subject.
2. User defines authorized scope.
3. User runs connector pack.
4. System normalizes observations into assertions and account discoveries.
5. User captures profile URLs and reviews discoveries.
6. Confirmed discoveries can be promoted into new seeds.
7. Graph and entity resolution show confidence, contradictions, and evidence.
8. User exports a signed, redacted client/court bundle.

### Team Workflow

1. Admin creates team membership.
2. Analysts share cases, notes, assignments, and review queues.
3. Admin monitors usage, failed jobs, audit events, and connector health.
4. Team exports case bundles with custody and audit manifests.

## 3. Plans, Entitlements, And Pricing

Initial pricing:

| Plan | Price | Purpose |
| --- | ---: | --- |
| Free | $0 | Trial and light evaluation |
| Weekly | $9/week | Short investigations |
| Starter | $29/month | Solo light analyst |
| Pro | $79/month | Primary paid tier |
| Team | $199/month | 3-seat team |
| Pro 3 Month | $199 | Discounted Pro |
| Pro 6 Month | $379 | Discounted Pro |
| Pro Yearly | $699 | Discounted Pro |
| Lifetime Early Access | $999-$1,499 | Usage-capped early offer |

Entitlement keys:

| Key | Free | Weekly | Starter | Pro | Team |
| --- | ---: | ---: | ---: | ---: | ---: |
| `active_cases` | 1 | 3 | 10 | 50 | 200 |
| `subjects_per_month` | 3 | 15 | 50 | 250 | 1000 |
| `connector_runs_per_day` | 10 | 60 | 150 | 800 | 3000 |
| `browser_captures_per_day` | 2 | 20 | 50 | 300 | 1000 |
| `account_ingests_per_day` | 2 | 20 | 75 | 400 | 1200 |
| `signed_exports_per_month` | 0 | 3 | 10 | 100 | 500 |
| `graph_builds_per_day` | 1 | 10 | 25 | 150 | 500 |
| `storage_gb` | 0.25 | 2 | 10 | 100 | 500 |
| `team_seats` | 1 | 1 | 1 | 1 | 3 |
| `watermark_exports` | true | false | false | false | false |

Rules:

- Paid tiers raise quotas and unlock features.
- Paid tiers never bypass scope, authorization, or responsible-use gates.
- Lifetime plans are Pro-like and monthly usage-capped.
- Quotas can be overridden by admin with an audit event.

## 4. Data Model And Ownership

Core relationships:

```text
user -> membership -> usage_events -> quota_periods
user/team -> cases -> subjects -> seeds
subject -> connector_runs -> raw_artifacts -> observations -> assertions
assertions -> account_discoveries -> promoted_seeds
case/subject -> evidence_captures -> custody_events
case/subject -> graphs -> nodes/edges/merge_candidates
case/subject -> exports -> manifests -> files/hashes
admin -> billing_events/audit_logs/hidden_service_status
```

Required tables:

- `membership_plans`
- `user_memberships`
- `usage_events`
- `usage_counters`
- `billing_events`
- `quota_overrides`
- `case_records`
- `case_events`
- `spine_subjects`
- `spine_seeds`
- `spine_connector_runs`
- `spine_raw_artifacts`
- `spine_observations`
- `spine_dossier_assertions`
- `spine_validation_events`
- `account_discoveries`
- `evidence_captures`
- `custody_events`
- `identity_graphs`
- `identity_nodes`
- `identity_edges`
- `identity_merge_candidates`
- `export_records`
- `export_files`
- `responsible_use_scope`
- `policy_gate_events`
- `hidden_service_status`

## 5. Enforcement Gate Contract

Every mutating workflow must call gates in this order:

1. Authentication
2. Role permission
3. Membership entitlement
4. Quota/rate limit
5. Responsible-use scope
6. Action-specific validation
7. Audit event

Gate result shape:

```json
{
  "allowed": false,
  "user_id": 12,
  "plan": "free",
  "action": "signed_export",
  "quota_key": "signed_exports_per_month",
  "used": 0,
  "limit": 0,
  "resets_at": "2026-06-01T00:00:00Z",
  "scope_state": "authorized",
  "upgrade_required": true,
  "reason": "Signed exports require Weekly or higher."
}
```

Workflows requiring gates:

- Signup
- Case create/update/delete
- Subject create
- Connector run
- Account discovery ingest
- Account discovery promotion
- Browser capture
- Graph build
- Dossier export
- Signed bundle export
- Admin membership change
- Backup/restore

## 6. Case Management

MVP:

- Cases, subjects, tags, notes, priority, review state, activity feed.

Production:

- Assignments, due dates, saved views, evidence attachments, audit by case.

Premium:

- Team queues, SLA filters, reusable case templates, review dashboards.

Acceptance tests:

- Free user cannot exceed active case quota.
- Case activity records subject, capture, account discovery, and export events.
- Team member can only access assigned/shared cases.

## 7. Subject Spine And Connectors

MVP:

- Seeds, connector runs, raw artifacts, normalized observations, assertions.

Production:

- Connector trust scoring, source refs, evidence refs, review queues.

Premium:

- Connector SDK, marketplace, fixtures, install validation, platform confidence.

Acceptance tests:

- Connector run writes raw artifact and SHA-256.
- Observation creates source/evidence refs.
- Assertions remain `unreviewed` until analyst action.
- Rejected assertions reduce connector trust.

## 8. Account Discovery

MVP:

- Ingest `account_presence` and `profile_url` observations.
- Create reviewable account discoveries.
- Promote confirmed discoveries into new seeds.

Production:

- Optional profile capture, capture IDs, review history, seed promotion audit.

Premium:

- Bulk discovery review, auto-capture policies, scheduled recapture, account
  change alerts.

Acceptance tests:

- Socialscan-style account observation creates account discovery.
- Profile URL discovery can generate capture artifacts.
- Confirmed discovery can promote a URL/username seed.
- Rejected discovery does not enter export as confirmed identity.

## 9. Evidence Capture And Chain Of Custody

MVP:

- HTML/import capture, SHA-256, capture record, verification.

Production:

- Browser screenshot, PDF, MHTML, capture manifest, custody event.

Premium:

- Scheduled recapture, diff view, WARC adapter, evidence retention policies.

Acceptance tests:

- Every capture artifact has hash, MIME type, size, actor, timestamp.
- Manifest verifies.
- Missing/tampered artifact fails verification.
- Captures appear in case/subject timeline.

## 10. Entity Resolution

MVP:

- Classification: human, organization, alias cluster, bot, hybrid, unresolved.
- Confidence and explanation.

Production:

- Confidence deltas, contradictions, source contribution, manual override audit.

Premium:

- Merge suggestions, identity clustering, repeated-asset matching, avatar hash
  correlation.

Acceptance tests:

- Single-source identity claim stays reviewable.
- Contradictions appear in export blockers.
- Manual override records actor, reason, and timestamp.

## 11. Graph UX

MVP:

- Graph payload, nodes, edges, confidence, evidence refs.

Production:

- Interactive graph canvas with filters, side panel, contradiction overlay.

Premium:

- Timeline animation, clustering, graph export, saved graph views.

Node types:

- subject, alias, account, email, phone, domain, URL, artifact, source, case,
  connector, assertion.

Edge types:

- seed, expanded_to, profile_url, linked_email, linked_domain, same_alias,
  same_avatar, evidence_for, contradicts, belongs_to_case.

Acceptance tests:

- Account discoveries appear as account/URL nodes.
- Edges include source/evidence refs.
- Filters do not hide export blockers by default.

## 12. Analyst Workbench UX

First screen for logged-in users:

- Active cases
- Review queues
- Account discoveries
- High-risk assertions
- Contradictions
- Export blockers
- Recent captures
- Jobs
- Connector health
- Usage/quota badge

UX standards:

- Dense, analyst-first layouts.
- Clear empty/error/loading states.
- No marketing-style hero once logged in.
- One-click route from claim to evidence.
- Upgrade prompts explain value and exact blocked capability.

Acceptance tests:

- Viewer cannot run scans.
- Analyst can run allowed workflows within quota.
- Blocked action gives useful plan/quota message.

## 13. Dossier And Export Builder

MVP:

- JSON, HTML, Markdown, CSV dossier sections.

Production:

- PDF, signed ZIP, manifest viewer, bundle verification, redaction presets.

Premium:

- Court/client/internal templates, export diff, watermark controls, scheduled
  recurring exports.

Court/client-ready acceptance criteria:

- Rejected claims excluded by default.
- Unreviewed/single-source claims clearly marked.
- Source refs visible.
- Evidence/custody summary included.
- Manifest hash verifies.
- Bundle hash verifies.
- Redaction preset recorded.
- Export blockers shown before release.

## 14. Responsible-Use Controls

Required controls:

- Authorization banner.
- Scope file.
- Target allowlist/blocklist.
- Case scope.
- Connector/capture/export gates.
- Sensitive-data redaction defaults.
- Export warnings.
- Policy gate audit events.

Acceptance tests:

- Blocklisted target cannot be captured, scanned, or exported.
- Paid user is still blocked by scope.
- Policy gate event records allow/warn/block.

## 15. Billing And Membership

MVP:

- Internal plans, manual admin assignment, usage counters, admin overrides.

Production:

- Stripe Checkout, webhook verification, subscription sync, billing events.

Premium:

- Team seats, lifetime packs, invoices, usage-based add-ons.

Stripe mapping:

- `membership_plans.stripe_price_id`
- `user_memberships.stripe_customer_id`
- `user_memberships.stripe_subscription_id`
- `billing_events.provider_event_id`
- Webhook idempotency on `provider_event_id`.

Failed payment policy:

- 3-day grace period.
- Then downgrade to Free or `past_due_limited`.
- Preserve cases and data; block new paid-only actions.

Cancellation policy:

- Access remains until paid period end.
- Downgrade at expiration.
- Exports remain accessible unless retention policy removes them.

## 16. Signup And Abuse Controls

MVP:

- Free signup, password policy, default free membership.

Production:

- Signup throttling, login throttling, account suspension, quota enforcement.

Premium:

- Email verification, Tor-friendly proof-of-work, TOTP/passkeys.

Acceptance tests:

- Signup creates user and free membership.
- Too many signups from same key are blocked.
- Suspended user cannot run workflows.

## 17. Tor Hidden-Service Deployment

Deployment modes:

- `dev-local`: local app, SQLite, no Tor requirement.
- `prod-tor-only`: app exposed only through Tor hidden service.
- `prod-clearnet-admin-disabled`: optional future mode; admin disabled on
  clearnet unless explicitly enabled.

Production requirements:

- App binds to internal/local interface only.
- Persistent onion keys stored in protected volume.
- Onion hostname visible in admin status.
- Hidden-service key backup documented.
- Key rotation runbook documented.
- Direct public app port disabled.
- Tor health smoke test.

Acceptance tests:

- Docker smoke confirms onion hostname exists.
- App health passes inside Tor deployment.
- Direct public port is not exposed in Tor-only profile.

## 18. Security And Privacy

Required:

- Strong secret validation.
- Secure cookies.
- CSRF.
- CSP/security headers.
- Role-based access.
- Audit logs.
- Encrypted backups.
- No secrets in logs.
- Admin-only destructive actions.
- Deletion confirmation.
- Restore procedure.
- Rate-limited auth.

Advanced:

- TOTP/passkeys.
- Signed audit ledger.
- Per-case encryption.
- Key rotation UI.
- Data deletion/export request workflow.

## 19. Background Jobs

Job types:

- Connector run.
- Account discovery ingest.
- Profile capture.
- Graph build.
- Dossier export.
- Bundle build.
- Backup.
- Cleanup.
- Retention.
- Trust metric refresh.

Requirements:

- Jobs record user, case, subject, quota decision, scope decision.
- Jobs are cancellable.
- Failed jobs are inspectable.
- Paid tiers can receive higher queue priority.

## 20. Admin Console

Required pages:

- Users.
- Memberships.
- Usage.
- Billing events.
- Connector health.
- Connector marketplace.
- Hidden-service status.
- Audit logs.
- Policy gates.
- System health.
- Backups.
- Jobs.

Admin actions:

- Suspend user.
- Change plan.
- Reset quota.
- Inspect usage.
- Disable connector.
- Force backup.
- Verify hidden service.
- Requeue/cancel failed jobs.

## 21. API Surface

Groups:

```text
/api/v1/account/*
/api/v1/admin/*
/api/v1/cases/*
/api/v1/spine/*
/api/v1/evidence/*
/api/v1/exports/*
/api/v1/connectors/*
/api/v1/jobs/*
/api/v1/responsible-use/*
```

Every mutation must enforce the gate contract in Section 5.

## 22. Implementation Matrix

| Area | MVP | Production | Premium |
| --- | --- | --- | --- |
| Cases | CRUD, tags | audit, assignment | teams, saved views |
| Capture | HTML/import | browser/PDF/MHTML | scheduled recapture |
| Export | JSON/HTML | signed ZIP/PDF | court/client templates |
| Graph | payload | interactive graph | clustering/timeline |
| Billing | manual plans | Stripe | teams/lifetime |
| Tor | compose config | smoke-tested hidden service | key rotation status |
| Account discovery | queue | capture + promote | recapture/change alerts |
| Connectors | run + normalize | trust telemetry | SDK + marketplace |

## 23. Milestone Plan

### v8.2.0 Membership + Quotas

- Plans, memberships, usage events, quota gates, free signup, admin membership
  management, account usage page.

### v8.3.0 Billing

- Stripe Checkout, webhooks, billing events, grace period, cancellation sync.

### v8.4.0 Tor Production

- Hidden-service status page, hardened Compose profile, Tor smoke, key backup
  and rotation runbook.

### v8.5.0 Analyst UX Polish

- Workbench redesign, discovery detail, graph filters, queue drilldowns, saved
  filters, user-friendly quota/upgrade states.

### v8.6.0 Export/Dossier Superiority

- Export diff, dossier presets, court/client/internal bundles, parity checks,
  verification UX.

### v8.7.0 Connector SDK + Marketplace

- Connector manifest schema, fixture runner, validation UX, trust badges, SDK
  docs.

### v9.0.0 Production Release

- Security review, docs complete, deployment runbook, final smoke matrix, admin
  console, pricing live.

## 24. Testing Matrix

Required tests:

- Signup creates free membership.
- Quota allows under limit.
- Quota blocks over limit with useful message.
- Paid plan unlocks paid capabilities.
- Scope blocks paid users.
- Admin can change membership.
- Usage event recorded for gated actions.
- Connector run creates artifact/observation/assertion.
- Account discovery ingest creates queue item.
- Confirmed discovery promotes seed.
- Capture verifies hash.
- Export bundle verifies manifest and ZIP hash.
- Tor hidden-service config renders and smokes.
- Backup/restore covers new tables.
- Billing webhook idempotency.

Release checks:

```bash
ruff check src tests scripts
pre-commit run --all-files
pytest -q
make production-smoke
make backup-restore-smoke
make production-docker-smoke
make ci
```

## 25. Definition Of Finished

The product is complete when:

- Free users can sign up safely.
- Every user has a plan and visible usage.
- Quotas protect expensive and high-risk actions.
- Paid memberships unlock clear value.
- Investigations are case-first.
- Connector runs produce evidence-backed assertions.
- Discovered accounts enter review before promotion.
- Captures are hashed, manifest-backed, and verifiable.
- Chain-of-custody records sensitive evidence actions.
- Graph and entity resolution are usable by an analyst.
- Dossiers are signed, redacted, reproducible, and export-blocker aware.
- Responsible-use gates apply everywhere.
- Tor hidden-service deployment is smoke-tested and documented.
- Admin can manage users, plans, connectors, jobs, backups, and audit.
- All release checks pass.
- README, RUNBOOK, CHANGELOG, release notes, and this spec are current.
