from __future__ import annotations

import hashlib
import importlib

import pytest


def _configure_tmp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "montreal-adapter.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SOCMINT_DATA_DIR", str(tmp_path))

    from src.socmint import database

    importlib.reload(database)
    from src.socmint import montreal_46_adapter_control

    importlib.reload(montreal_46_adapter_control)
    return database, montreal_46_adapter_control


def _plan_hash(label: str = "approved-plan") -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_adapter_defaults_to_passive_without_writes(monkeypatch, tmp_path):
    _, control = _configure_tmp_db(monkeypatch, tmp_path)

    state = control.get_adapter_state(46)

    assert state["case_id"] == "46MONST"
    assert state["system_maximum_mode"] == "passive"
    assert state["case_mode"] == "passive"
    assert state["effective_mode"] == "passive"
    assert state["permissions"]["inventory"] is True
    assert state["permissions"]["prepare_import"] is True
    assert state["permissions"]["execute_controlled_import"] is False
    assert state["permissions"]["mutate_dossier"] is False
    assert state["authoritative_case_records_changed"] is False
    assert control.passive_report_footer() == "No authoritative case records were changed."


def test_effective_mode_uses_least_permissive_control(monkeypatch, tmp_path):
    _, control = _configure_tmp_db(monkeypatch, tmp_path)
    plan_hash = _plan_hash()

    control.set_system_maximum_mode(
        "on", actor="admin", reason="permit controlled testing", confirmed=True
    )
    control.set_case_adapter_mode(
        46,
        "on",
        actor="operator",
        reason="approved controlled import",
        confirmed=True,
        import_plan_sha256=plan_hash,
    )

    assert control.get_adapter_state(46)["effective_mode"] == "on"
    assert control.get_adapter_state(46, requested_mode="passive")["effective_mode"] == "passive"

    control.set_system_maximum_mode(
        "passive", actor="admin", reason="system-wide safety cap"
    )
    capped = control.get_adapter_state(46, requested_mode="on")
    assert capped["case_mode"] == "on"
    assert capped["effective_mode"] == "passive"
    assert capped["permissions"]["execute_controlled_import"] is False


def test_off_to_on_transition_is_prohibited(monkeypatch, tmp_path):
    _, control = _configure_tmp_db(monkeypatch, tmp_path)

    control.set_case_adapter_mode(46, "off", actor="operator", reason="maintenance")

    with pytest.raises(ValueError, match="off to on is prohibited"):
        control.set_case_adapter_mode(
            46,
            "on",
            actor="operator",
            reason="skip preview",
            confirmed=True,
            import_plan_sha256=_plan_hash(),
        )

    control.set_case_adapter_mode(
        46, "passive", actor="operator", reason="prepare preview"
    )
    enabled = control.set_case_adapter_mode(
        46,
        "on",
        actor="operator",
        reason="preview approved",
        confirmed=True,
        import_plan_sha256=_plan_hash(),
    )
    assert enabled["new_mode"] == "on"


def test_on_requires_confirmation_and_plan_binding(monkeypatch, tmp_path):
    _, control = _configure_tmp_db(monkeypatch, tmp_path)

    control.set_system_maximum_mode(
        "on", actor="admin", reason="permit controlled imports", confirmed=True
    )

    with pytest.raises(ValueError, match="explicit operator confirmation"):
        control.set_case_adapter_mode(
            46,
            "on",
            actor="operator",
            reason="not confirmed",
            import_plan_sha256=_plan_hash(),
        )

    with pytest.raises(ValueError, match="approved import_plan_sha256"):
        control.set_case_adapter_mode(
            46,
            "on",
            actor="operator",
            reason="missing plan",
            confirmed=True,
        )


def test_controlled_import_requires_exact_active_plan(monkeypatch, tmp_path):
    _, control = _configure_tmp_db(monkeypatch, tmp_path)
    plan_hash = _plan_hash()

    control.set_system_maximum_mode(
        "on", actor="admin", reason="permit controlled imports", confirmed=True
    )
    control.set_case_adapter_mode(
        "46MONST",
        "on",
        actor="operator",
        reason="approved preview",
        confirmed=True,
        import_plan_sha256=plan_hash,
    )

    unconfirmed = control.authorize_operation(
        46,
        "execute_controlled_import",
        requested_mode="on",
        import_plan_sha256=plan_hash,
    )
    wrong_plan = control.authorize_operation(
        46,
        "execute_controlled_import",
        requested_mode="on",
        confirmed=True,
        import_plan_sha256=_plan_hash("different"),
    )
    allowed = control.authorize_operation(
        46,
        "execute_controlled_import",
        requested_mode="on",
        confirmed=True,
        import_plan_sha256=plan_hash,
    )

    assert unconfirmed["blocker"] == "explicit_execution_confirmation_required"
    assert wrong_plan["blocker"] == "approved_import_plan_binding_required"
    assert allowed["status"] == "allowed"
    assert allowed["authoritative_case_records_changed"] is False


def test_cowdy_scope_is_narrow_and_non_adverse(monkeypatch, tmp_path):
    _, control = _configure_tmp_db(monkeypatch, tmp_path)

    scope = control.get_adapter_state("46 Montreal Street")["scope"]
    cowdy = scope["cowdy_street"]

    assert cowdy == {
        "upstairs_noise": True,
        "water_leak": True,
        "other_issues": False,
        "landlord_adverse_characterization": False,
    }


def test_mode_changes_are_append_only_audit_events(monkeypatch, tmp_path):
    database, control = _configure_tmp_db(monkeypatch, tmp_path)

    control.set_case_adapter_mode(46, "off", actor="operator", reason="maintenance")
    control.set_case_adapter_mode(46, "passive", actor="operator", reason="resume preview")

    events = database.get_audit_events(action="case_adapter_mode_changed")
    assert len(events) == 2
    newest = events[0]
    assert newest.actor == "operator"
    assert '"previous_mode": "off"' in newest.details
    assert '"new_mode": "passive"' in newest.details
