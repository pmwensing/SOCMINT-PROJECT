from src.socmint.route_enforcement import route_enforcement_report
from src.socmint.route_enforcement import route_enforcement_summary
from src.socmint.wsgi import app


def test_route_enforcement_report_shape():
    report = route_enforcement_report(app)

    assert report["schema"] == "socmint.route_enforcement.v9_0_3"
    assert report["status"] in {"pass", "fail"}
    assert report["total_routes"] >= report["mutating_routes"]
    assert isinstance(report["violations"], list)
    assert isinstance(report["warnings"], list)


def test_route_enforcement_summary_matches_report():
    report = route_enforcement_report(app)
    summary = route_enforcement_summary(app)

    assert summary["schema"] == "socmint.route_enforcement.v9_0_3"
    assert summary["status"] == report["status"]
    assert summary["mutating_routes"] == report["mutating_routes"]
    assert summary["violation_count"] == report["violation_count"]
