from src.socmint.connectors import list_connectors, run_connector


def test_registry_contains_v5_2_connectors():
    names = {item["name"] for item in list_connectors()}
    assert {
        "sherlock",
        "holehe",
        "maigret",
        "h8mail",
        "socialscan",
        "phoneinfoga",
    }.issubset(names)


def test_missing_binary_records_safe_dry_run(monkeypatch):
    monkeypatch.setattr(
        "src.socmint.connectors.executable_available",
        lambda command: False,
    )
    result = run_connector("sherlock", "exampleuser", "username")
    assert result["status"] == "dry_run"
    assert result["connector"] == "sherlock"
    assert "raw" not in result or result["status"] == "dry_run"


def test_unsupported_target_type_is_skipped():
    result = run_connector("holehe", "exampleuser", "username")
    assert result["status"] == "skipped"


def test_phoneinfoga_supports_phone_targets(monkeypatch):
    monkeypatch.setattr(
        "src.socmint.connectors.executable_available",
        lambda command: False,
    )
    result = run_connector("phoneinfoga", "+14155552671", "phone")
    assert result["status"] == "dry_run"
    assert result["command"] == ["phoneinfoga", "scan", "-n", "+14155552671"]
