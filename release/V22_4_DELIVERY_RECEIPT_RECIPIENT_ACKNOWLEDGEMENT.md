# v22.4 Delivery Receipt and Recipient Acknowledgement

Consumes the latest recorded v22.3 distribution result and stores delivery success or failure metadata as a separate immutable delivery receipt.

Recipient acknowledgement is recorded separately from the delivery receipt and may only reference a successful delivered receipt.

The workspace shows delivery state, receipt metadata, outstanding acknowledgement status, and completion state while preserving the original dispatch record unchanged.

Delivery receipt metadata may include provider message id, transport status, delivered timestamp, failure code, failure detail, and operator note.

Recipient acknowledgement metadata may include recipient name, acknowledgement method, acknowledgement timestamp, and operator note.

Routes:

- `GET /api/v1/dossier-release/<case_id>/delivery-state`
- `POST /api/v1/dossier-release/<case_id>/delivery-receipt`
- `POST /api/v1/dossier-release/<case_id>/recipient-acknowledgement`

Existing audit-log storage is reused. The dispatch, export, authorization, and preview records remain unchanged, and no migration is introduced.
