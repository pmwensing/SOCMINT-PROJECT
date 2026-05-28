from socmint.dashboard import create_app
from socmint.dossier_readiness_routes_v13 import register_dossier_readiness_routes
from socmint.dossier_readiness_v13 import ReadinessInput, compute_dossier_readiness


def test_readiness_blocks_without_subject():
    result = compute_dossier_readiness(ReadinessInput(subject_id=None, subject_exists=False))

    assert result["schema"] == "socmint.dossier_readiness.v13_4"
    assert result["state"] == "blocked"
    assert result["draft_export_allowed"] is False
    assert result["final_export_allowed"] is False
    assert result["next_actions"][0]["key"] == "create_subject"


def test_readiness_blocks_without_seed():
    result = compute_dossier_readiness(
        ReadinessInput(subject_id=1, subject_exists=True, seed_count=0)
    )

    assert result["state"] == "blocked"
    assert "Add at least one seed or target." in result["blockers"]
    assert result["next_actions"][0]["key"] == "add_seed"


def test_readiness_needs_collection_without_findings():
    result = compute_dossier_readiness(
        ReadinessInput(subject_id=1, subject_exists=True, seed_count=1, finding_count=0)
    )

    assert result["state"] == "needs_review"
    assert result["next_actions"][0]["key"] == "run_collection"
    assert result["draft_export_allowed"] is False


def test_readiness_needs_review_with_pending_items():
    result = compute_dossier_readiness(
        ReadinessInput(
            subject_id=1,
            subject_exists=True,
            seed_count=1,
            finding_count=3,
            pending_review_count=2,
        )
    )

    assert result["state"] == "needs_review"
    assert result["next_actions"][0]["key"] == "review_findings"
    assert result["final_export_allowed"] is False


def test_readiness_allows_draft_after_findings():
    result = compute_dossier_readiness(
        ReadinessInput(subject_id=7, subject_exists=True, seed_count=1, finding_count=3)
    )

    assert result["state"] == "draft_ready"
    assert result["draft_export_allowed"] is True
    assert result["final_export_allowed"] is False
    assert result["next_actions"][0]["href"] == "/spine/subjects/7/full-report"


def test_readiness_exported_when_report_exists():
    result = compute_dossier_readiness(
        ReadinessInput(
            subject_id=7,
            subject_exists=True,
            seed_count=1,
            finding_count=3,
            report_count=1,
        )
    )

    assert result["state"] == "exported"
    assert result["draft_export_allowed"] is True
    assert result["final_export_allowed"] is True


def test_dossier_readiness_routes_register_once():
    app = create_app()
    register_dossier_readiness_routes(app)
    register_dossier_readiness_routes(app)

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/v1/subjects/<int:subject_id>/dossier/readiness" in rules
    assert "/api/v1/command-center/dossier-readiness" in rules
