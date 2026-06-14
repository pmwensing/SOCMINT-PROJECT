# v22.5 Failed Delivery, Recall, and Reissue Controls

Adds an explicit failed-delivery review, explicit recall requests, and reissue authorization tied to the original package and recipient history.

The failed-delivery review records the source receipt, failure metadata, root cause, resolution plan, reviewer, and note as a separate immutable event.

Recall requests reference the original distribution, export package, recipient, and delivery channel. Recall is blocked after recipient acknowledgement has already been recorded.

Reissue authorization records the original distribution, package, recipient, channel, receipt, delivery result, and any recall request before authorizing a target recipient and target channel.

Routes:

- `GET /api/v1/dossier-release/<case_id>/delivery-recovery`
- `POST /api/v1/dossier-release/<case_id>/failed-delivery-review`
- `POST /api/v1/dossier-release/<case_id>/recall`
- `POST /api/v1/dossier-release/<case_id>/reissue-authorization`

All reviews, recalls, and reissues are immutable records created without altering the original dispatch, receipt, or acknowledgement events. Existing audit-log storage is reused, and no migration is introduced.
