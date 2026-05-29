from __future__ import annotations

from flask import jsonify, request

from .normalization_review_queue_v13 import build_normalization_review_queue


def parse_min_confidence(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def register_normalization_review_queue_routes(app) -> None:
    if "api_normalization_review_queue_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def api_normalization_review_queue_v13():
        subject_id_raw = request.args.get("subject_id")
        state = request.args.get("review_state")
        kind = request.args.get("kind")
        min_confidence = parse_min_confidence(request.args.get("min_confidence"))
        limit_raw = request.args.get("limit", "100")
        subject_id = int(subject_id_raw) if subject_id_raw else None
        limit = max(1, min(int(limit_raw), 500))
        return jsonify(
            build_normalization_review_queue(
                subject_id=subject_id,
                review_state=state,
                kind=kind,
                min_confidence=min_confidence,
                limit=limit,
            )
        )

    app.add_url_rule(
        "/api/v1/review/normalization-queue",
        endpoint="api_normalization_review_queue_v13",
        view_func=api_normalization_review_queue_v13,
        methods=["GET"],
    )
