from src.socmint.certification import certification_report
from src.socmint.certification import certification_summary


def test_certification_report_shape():
    report = certification_report()

    assert report["schema"] == "socmint.certification.v9_5_0"
    assert report["score"] <= report["max_score"]
    assert "production_release" in report["domains"]
    assert "billing_integration" in report["domains"]
    assert isinstance(report["blockers_or_conditions"], list)


def test_certification_summary_matches_report():
    report = certification_report()
    summary = certification_summary()

    assert summary["schema"] == "socmint.certification.v9_5_0"
    assert summary["state"] == report["state"]
    assert summary["score"] == report["score"]
    assert summary["percentage"] == report["percentage"]
