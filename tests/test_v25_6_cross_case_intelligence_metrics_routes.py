from pathlib import Path

from src.socmint.dashboard import create_app
from src.socmint.dossier_assembly_routes_v21_0 import (
    register_dossier_assembly_routes_v21_0,
)


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")
    app = create_app()
    register_dossier_assembly_routes_v21_0(app)
    return app


def test_v25_6_metrics_routes_apply_scope_and_render(tmp_path, monkeypatch):
    from src.socmint import cross_case_intelligence_metrics_routes_v25_6 as routes

    captured = []
    payload = {
        "schema": "socmint.cross_case_intelligence_metrics.v25_6",
        "version": "v25.6.0",
        "status": "ready",
        "generated_at": "2026-06-16T09:00:00+00:00",
        "access_scope": {
            "mode": "restricted",
            "allowed_case_ids": ["case-alpha", "case-bravo"],
        },
        "metrics": {
            "candidate_volume": {
                "total": 3,
                "by_category": {"entities": 1},
                "repeated_patterns": 1,
                "visible_cases": 2,
                "source_records": 8,
            },
            "review_dispositions": {
                "total_reviews": 2,
                "reviewed_candidates": 2,
                "all_decisions": {"accept": 1, "reject": 1},
                "latest_decisions": {"accept": 1, "reject": 1},
                "review_coverage_percent": 66.67,
            },
            "confirmation_conversion": {
                "confirmed_links": 1,
                "accepted_reviews": 1,
                "latest_accepted_reviews": 1,
                "candidate_to_confirmed_percent": 33.33,
                "accepted_to_registered_percent": 100.0,
            },
            "graph_density": {
                "nodes": 4,
                "edges": 3,
                "density_percent": 50.0,
                "edges_per_node": 0.75,
                "average_degree": 1.5,
                "median_degree": 1.5,
                "graph_sha256": "g" * 64,
            },
            "cross_case_reach": {
                "candidate_case_count": 2,
                "confirmed_case_count": 2,
                "visible_case_count": 2,
                "confirmed_case_reach_percent": 100.0,
                "average_cases_per_confirmed_link": 2.0,
                "median_cases_per_confirmed_link": 2.0,
                "maximum_cases_per_confirmed_link": 2,
            },
            "source_occurrence_coverage": {
                "candidate_occurrences": 6,
                "confirmed_occurrences": 4,
                "coverage_percent": 66.67,
            },
            "impact_breadth": {
                "analyzed_links": 1,
                "average_breadth_score": 7.0,
                "median_breadth_score": 7.0,
                "maximum_breadth_score": 7,
                "links": [],
            },
            "analyst_throughput": {
                "analyst_count": 1,
                "total_reviews": 2,
                "analysts": [
                    {
                        "analyst": "alice",
                        "review_count": 2,
                        "active_review_days": 1,
                        "reviews_per_active_day": 2.0,
                        "disposition_counts": {"accept": 1, "reject": 1},
                    }
                ],
            },
            "confidence_indicators": {
                "score": 76.67,
                "band": "moderate",
                "components": {
                    "review_coverage_percent": 66.67,
                    "accepted_materialization_percent": 100.0,
                    "source_occurrence_coverage_percent": 66.67,
                    "cross_case_reach_percent": 100.0,
                    "graph_support_percent": 50.0,
                },
                "interpretation": "operational_indicator_not_probability_or_factual_certainty",
            },
        },
        "metrics_sha256": "m" * 64,
        "confidence_is_operational_indicator": True,
        "confidence_is_not_probability": True,
        "source_records_mutated": False,
        "review_history_mutated": False,
        "confirmed_link_registry_mutated": False,
        "graph_mutated": False,
        "impact_records_created": False,
        "metrics_record_created": False,
        "next_action": "review_cross_case_intelligence_metrics",
    }

    def build(**kwargs):
        captured.append(kwargs)
        return payload

    monkeypatch.setattr(routes, "build_cross_case_intelligence_metrics", build)
    client = _app(tmp_path, monkeypatch).test_client()
    assert client.get("/api/v1/cross-case-intelligence/metrics").status_code == 401
    assert client.get("/cross-case-intelligence/metrics").status_code in {302, 303}

    with client.session_transaction() as sess:
        sess["user"] = "analyst"
        sess["allowed_case_ids"] = ["case-alpha", "case-bravo"]

    ui = client.get("/cross-case-intelligence/metrics")
    api = client.get("/api/v1/cross-case-intelligence/metrics")

    assert ui.status_code == 200
    assert b"Cross-Case Intelligence Metrics and Confidence" in ui.data
    assert b"Candidate Volume and Review Dispositions" in ui.data
    assert b"Confirmation Conversion" in ui.data
    assert b"Graph Density and Cross-Case Reach" in ui.data
    assert b"Source-Occurrence Coverage and Impact Breadth" in ui.data
    assert b"Analyst Throughput" in ui.data
    assert b"Confidence Components" in ui.data
    assert b"not a probability or statement of factual certainty" in ui.data
    assert b"alice" in ui.data
    assert api.status_code == 200
    assert api.get_json()["metrics"]["candidate_volume"]["total"] == 3
    assert all(
        item["allowed_case_ids"] == {"case-alpha", "case-bravo"} for item in captured
    )


def test_v25_6_release_note_and_no_migration():
    note = Path(
        "release/V25_6_CROSS_CASE_INTELLIGENCE_METRICS_CONFIDENCE.md"
    ).read_text(encoding="utf-8")
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v25_6*")
    ]
    for phrase in (
        "candidate volume",
        "review dispositions",
        "confirmation conversion",
        "graph density",
        "cross-case reach",
        "source-occurrence coverage",
        "impact breadth",
        "analyst throughput",
        "confidence indicators",
        "operational indicator",
        "not a probability",
        "read-only",
    ):
        assert phrase in note
    assert migrations == []
