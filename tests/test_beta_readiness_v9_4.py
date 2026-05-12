from src.socmint.beta_readiness import beta_doc_status
from src.socmint.beta_readiness import beta_onboarding_steps
from src.socmint.beta_readiness import beta_readiness_summary


def test_beta_doc_status_detects_required_docs(tmp_path):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    for name in [
        "RESPONSIBLE_USE_POLICY.md",
        "PRIVACY_POLICY.md",
        "TERMS_OF_USE.md",
        "OPERATOR_ONBOARDING.md",
        "PUBLIC_BETA_CHECKLIST.md",
    ]:
        (docs_dir / name).write_text("ok")

    status = beta_doc_status(tmp_path)

    assert status["schema"] == "socmint.beta_readiness.v9_4_0"
    assert status["status"] == "ready"
    assert status["missing"] == []


def test_beta_readiness_summary_reports_missing_docs(tmp_path):
    summary = beta_readiness_summary(tmp_path)

    assert summary["schema"] == "socmint.beta_readiness.v9_4_0"
    assert summary["status"] == "needs_review"
    assert summary["missing_docs"]


def test_beta_onboarding_steps_are_case_scope_oriented():
    steps = beta_onboarding_steps()

    assert steps["schema"] == "socmint.beta_readiness.v9_4_0"
    assert any("authorized" in step.lower() for step in steps["steps"])
    assert any("export preflight" in step.lower() for step in steps["steps"])
