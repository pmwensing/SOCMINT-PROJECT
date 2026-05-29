from __future__ import annotations

from flask import render_template, request

from .normalization_review_queue_routes_v13 import parse_min_confidence
from .normalization_review_queue_v13 import build_normalization_review_queue


def register_normalization_review_ui_routes(app) -> None:
    if "normalization_review_queue_view_v13" in app.view_functions:
        return

    from .dashboard import login_required

    @login_required
    def normalization_review_queue_view_v13():
        subject_id_raw = request.args.get("subject_id")
        review_state = request.args.get("review_state") or "unreviewed"
        kind = request.args.get("kind") or ""
        min_confidence = parse_min_confidence(request.args.get("min_confidence"))
        subject_id = int(subject_id_raw) if subject_id_raw else None
        payload = build_normalization_review_queue(
            subject_id=subject_id,
            review_state=review_state,
            kind=kind or None,
            min_confidence=min_confidence,
            limit=100,
        )
        return render_template(
            "normalization_review_queue.html",
            payload=payload,
            subject_id=subject_id,
            review_state=review_state,
            kind=kind,
            min_confidence=min_confidence,
        )

    app.add_url_rule(
        "/review/normalization-queue",
        endpoint="normalization_review_queue_view_v13",
        view_func=normalization_review_queue_view_v13,
        methods=["GET"],
    )
