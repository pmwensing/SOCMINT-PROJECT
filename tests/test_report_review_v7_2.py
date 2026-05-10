from pathlib import Path

from socmint.dashboard import create_app
from socmint.report_review import (
    report_runs_payload,
    review_items_payload,
    review_summary,
    set_review_status,
)


def test_report_review_payload_shapes():
    summary = review_summary()
    items = review_items_payload()
    reports = report_runs_payload()

    assert summary["schema"] == "socmint.report_review.summary.v7_2"
    assert "review_item_count" in summary
    assert items["schema"] == "socmint.report_review.items.v7_2"
    assert "items" in items
    assert reports["schema"] == "socmint.report_review.runs.v7_2"
    assert "reports" in reports


def test_report_review_routes_registered():
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/reports/review" in rules
    assert "/api/v1/reports/review/summary" in rules
    assert "/api/v1/reports/review/items" in rules
    assert "/api/v1/reports/runs" in rules
    assert "/api/v1/reports/review/items/<path:item_id>" in rules


def test_sidecar_review_decision(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = set_review_status("findings:123", "approved", "looks good")

    assert result["updated"] is True
    assert result["sidecar"] is True
    assert Path(result["path"]).exists()
