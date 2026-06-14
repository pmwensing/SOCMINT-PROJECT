# v22.3 Secure Distribution Action

Consumes the latest valid authorization and acknowledged-ready preview, requires explicit final operator confirmation, and invokes the existing case-delivery execution path rather than creating a second transport engine.

The action validates authorization, export package, recipient, delivery channel, preview acknowledgement, and release readiness before dispatch.

On confirmation it adapts the authorized dossier context into the existing v15.6 execution-envelope contract, calls the v16.0 case-delivery operations builder with a `dispatch_confirmed` event, and records both the dispatch request and returned operations result.

Routes:

- `GET /api/v1/dossier-release/<case_id>/distribution-readiness`
- `POST /api/v1/dossier-release/<case_id>/dispatch`

Nothing is dispatched without explicit final operator confirmation. The source export, authorization, and preview records remain unchanged. The existing audit log is reused, and no migration is introduced.
