from pathlib import Path


REQUIRED_ROUTES = (
    "/publication-review",
    "/publication-review/product-review",
    "/api/v1/publication-review",
    "/api/v1/publication-review/candidates",
    "/api/v1/publication-review/draft-revisions",
    "/api/v1/publication-review/editorial-validations",
    "/api/v1/publication-review/release-approvals",
    "/api/v1/publication-review/published-revisions",
    "/api/v1/publication-review/supersessions",
    "/api/v1/publication-review/product-review-checkpoint",
)


def test_v31_7_production_wsgi_registers_publication_route_chain():
    content = Path("src/socmint/wsgi.py").read_text(encoding="utf-8")

    assert (
        "from .publication_review_routes_v31_0 import "
        "register_publication_review_routes_v31_0"
    ) in content
    assert "register_publication_review_routes_v31_0(app)" in content


def test_v31_7_required_route_contract_is_complete():
    assert len(REQUIRED_ROUTES) == 10
    assert len(set(REQUIRED_ROUTES)) == len(REQUIRED_ROUTES)
