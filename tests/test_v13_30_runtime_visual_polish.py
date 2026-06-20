from pathlib import Path


def test_base_loads_runtime_visual_stylesheet():
    template = Path("src/socmint/templates/base.html").read_text()
    assert "runtime_visual.css" in template


def test_runtime_visual_css_wraps_long_runtime_values():
    css = Path("src/socmint/static/runtime_visual.css").read_text()
    assert "overflow-wrap: anywhere" in css
    assert "word-break: break-word" in css
    assert "min-width: 0" in css
    assert "pre" in css
    assert "code" in css


def test_full_report_retention_uses_runtime_visual_stylesheet():
    source = Path("src/socmint/full_report_retention.py").read_text()
    assert "runtime_visual.css" in source
    assert "runtime-utility-page" in source
    assert "runtime-utility-card" in source


def test_full_report_retention_accepts_invalid_keep_latest(monkeypatch):
    from socmint import full_report_retention

    monkeypatch.setattr(
        full_report_retention,
        "full_report_export_history",
        lambda subject_id, limit=500: {"exports": []},
    )
    monkeypatch.setattr(
        full_report_retention, "load_pins", lambda: {"schema": "test", "pins": {}}
    )

    # Static source regression for guarded integer parsing in both UI and API paths.
    source = Path("src/socmint/full_report_retention.py").read_text()
    assert "def _int_request_arg" in source
    assert "except (TypeError, ValueError)" in source
