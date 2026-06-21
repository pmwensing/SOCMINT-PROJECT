from src.socmint import database
from src.socmint.case_findings_v20 import (
    build_dossier_promotion_package,
    decide_finding,
    propose_finding,
)
from src.socmint.dossier_package_import_v21_1 import (
    import_dossier_package,
    inspect_dossier_package_import,
)


def _setup(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'app.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    database.configure_database(url)


def _promote(suffix="1"):
    item = propose_finding(
        "case-alpha",
        {
            "text": f"Finding {suffix}",
            "claim_ids": [f"claim-{suffix}"],
            "evidence_ids": [f"evidence-{suffix}"],
            "confidence": "high",
        },
        actor="analyst",
    )
    decide_finding("case-alpha", item["finding_id"], "approve", actor="supervisor")
    return build_dossier_promotion_package(
        "case-alpha", actor="supervisor", promote=True
    )


def test_v21_1_import_and_duplicate(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    package = _promote()
    before = inspect_dossier_package_import("case-alpha")
    first = import_dossier_package("case-alpha", actor="operator")
    second = import_dossier_package("case-alpha", actor="operator")
    after = inspect_dossier_package_import("case-alpha")
    assert before["manifest_verified"] is True
    assert before["source_identity"]["package_id"] == package["package_id"]
    assert first["status"] == "imported"
    assert second["status"] == "duplicate"
    assert after["status"] == "imported_current"
    assert after["can_arrange"] is True


def test_v21_1_missing_and_stale(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert inspect_dossier_package_import("empty")["status"] == "blocked_no_package"
    _promote("1")
    import_dossier_package("case-alpha", actor="operator")
    _promote("2")
    result = inspect_dossier_package_import("case-alpha")
    assert result["status"] == "imported_stale"
    assert result["package_stale"] is True
    assert result["can_import"] is True
