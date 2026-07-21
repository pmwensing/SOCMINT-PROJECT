from src.socmint import operational_import_record_projection_v37_2 as projection


def test_v37_2_projection_exposes_parent_import_binding(monkeypatch):
    monkeypatch.setattr(
        projection,
        "current_batches",
        lambda: [
            {
                "operational_import_id": "import-a",
                "staged_record_batch_id": "batch-a",
                "batch_event_sha256": "a" * 64,
                "recorded_at": "2026-07-20T01:00:00+00:00",
                "records": [
                    {
                        "staged_record_id": "record-a",
                        "record_sha256": "b" * 64,
                        "initial_state": "accepted",
                    }
                ],
            }
        ],
    )
    records = projection.current_staged_record_projections("import-a")
    assert records == [
        {
            "staged_record_id": "record-a",
            "record_sha256": "b" * 64,
            "initial_state": "accepted",
            "operational_import_id": "import-a",
            "staged_record_batch_id": "batch-a",
            "batch_event_sha256": "a" * 64,
            "batch_recorded_at": "2026-07-20T01:00:00+00:00",
        }
    ]
    assert projection.find_staged_record_projection("record-a")[
        "operational_import_id"
    ] == "import-a"
    assert projection.current_staged_record_projections("other-import") == []
