from pathlib import Path

import pytest

from src.socmint.import_adapter_v37_2 import parse_export_text


FIXTURES = Path(__file__).resolve().parent / "fixtures/v37_imports"


@pytest.mark.parametrize(
    ("export_format", "filename"),
    [
        ("json", "fictional_records.json"),
        ("jsonl", "fictional_records.jsonl"),
        ("ndjson", "fictional_records.jsonl"),
        ("csv", "fictional_records.csv"),
        ("html", "fictional_records.html"),
    ],
)
def test_v37_2_parses_supported_synthetic_exports(export_format, filename):
    payload = (FIXTURES / filename).read_text(encoding="utf-8")
    result = parse_export_text(export_format, payload)
    assert result["schema"] == "socmint.import_adapter_result.v37_2"
    assert result["record_count"] == 2
    assert result["records"][0]["record_id"] == "fixture-1"
    assert result["records"][1]["entity"] == "Entity Beta"
    assert result["payload_persisted"] is False
    assert result["network_access_performed"] is False
    assert result["collection_performed"] is False


def test_v37_2_adapter_rejects_bad_contracts():
    with pytest.raises(ValueError, match="unsupported"):
        parse_export_text("xlsx", "data")
    with pytest.raises(ValueError, match="required"):
        parse_export_text("json", "")
    with pytest.raises(ValueError, match="list"):
        parse_export_text("json", '{"not_records": true}')
    with pytest.raises(ValueError, match="line 2"):
        parse_export_text("jsonl", '{"a":1}\nnot-json')
    with pytest.raises(ValueError, match="required"):
        parse_export_text("csv", "")
    with pytest.raises(ValueError, match="table header"):
        parse_export_text("html", "<table><tr><th>a</th></tr></table>")
