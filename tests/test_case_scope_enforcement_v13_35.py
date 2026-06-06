import pytest

from src.socmint import database as db


def test_spine_subjects_can_be_bound_and_filtered_by_case(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")

    alpha_id = db.create_spine_subject("Alpha", case_key="case-alpha")
    beta_id = db.create_spine_subject("Beta", case_key="case-beta")

    alpha_subjects = db.list_spine_subjects(case_key="case-alpha")

    assert [subject.id for subject in alpha_subjects] == [alpha_id]
    assert beta_id not in [subject.id for subject in alpha_subjects]
    assert db.get_spine_subject(alpha_id).case_key == "case-alpha"


def test_seed_creation_rejects_subject_outside_requested_case(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    subject_id = db.create_spine_subject("Alpha", case_key="case-alpha")

    with pytest.raises(ValueError, match="outside the requested case scope"):
        db.add_spine_seed(
            subject_id,
            "email",
            "alpha@example.test",
            "alpha@example.test",
            "hash-alpha",
            case_key="case-beta",
        )


def test_connector_run_rejects_cross_subject_seed(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    alpha_id = db.create_spine_subject("Alpha", case_key="case-alpha")
    beta_id = db.create_spine_subject("Beta", case_key="case-beta")
    beta_seed_id = db.add_spine_seed(
        beta_id,
        "email",
        "beta@example.test",
        "beta@example.test",
        "hash-beta",
        case_key="case-beta",
    )

    with pytest.raises(ValueError, match="outside the requested subject scope"):
        db.create_spine_connector_run(
            alpha_id,
            "email-check",
            beta_seed_id,
            "blocked",
            {"ok": False},
            case_key="case-alpha",
        )


def test_connector_run_accepts_matching_subject_seed_and_case(tmp_path):
    db.configure_database(f"sqlite:///{tmp_path / 'socmint.db'}")
    subject_id = db.create_spine_subject("Alpha", case_key="case-alpha")
    seed_id = db.add_spine_seed(
        subject_id,
        "email",
        "alpha@example.test",
        "alpha@example.test",
        "hash-alpha",
        case_key="case-alpha",
    )

    run_id = db.create_spine_connector_run(
        subject_id,
        "email-check",
        seed_id,
        "ok",
        {"ok": True},
        case_key="case-alpha",
    )

    runs = db.list_spine_connector_runs(subject_id=subject_id)
    assert runs[0].id == run_id
