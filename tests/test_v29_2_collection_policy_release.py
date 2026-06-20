from pathlib import Path


def test_v29_2_release_note_and_no_migration():
    note = Path("release/V29_2_AUTHORIZATION_SCOPE_COLLECTION_POLICY.md").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "Authorization, Scope, and Collection Policy",
        "permitted source classes",
        "collection purpose",
        "jurisdiction metadata",
        "case, entity, and source scope",
        "deny rules",
        "exclusions",
        "expiry",
        "review dates",
        "policy evaluation before authorization",
        "deny overrides allow",
        "administrator required",
        "explicit confirmation",
        "no connector execution",
        "no job mutation",
        "no case-access change",
        "no migration",
    ):
        assert phrase in note
    migrations = [
        path
        for directory in (Path("migrations"), Path("alembic"))
        if directory.exists()
        for path in directory.rglob("*v29_2*")
    ]
    assert migrations == []
