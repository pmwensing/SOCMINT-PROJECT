from pathlib import Path


def test_v31_7_browser_e2e_covers_complete_publication_workflow():
    path = Path("scripts/run_v31_7_publication_browser_e2e.py")
    content = path.read_text(encoding="utf-8")

    for required in (
        '"workspace"',
        '"product_review"',
        '"workspace_api"',
        '"candidates_api"',
        '"draft_revisions_api"',
        '"editorial_validations_api"',
        '"release_approvals_api"',
        '"published_revisions_api"',
        '"supersessions_api"',
        '"checkpoint_ready"',
        'register_publication_review_routes_v31_0(app)',
        'session["is_admin"] = True',
        'shutil.which("chromedriver")',
    ):
        assert required in content
