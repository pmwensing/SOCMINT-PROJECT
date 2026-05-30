from pathlib import Path


def test_command_center_exposes_v13_workflow_links():
    template = Path("src/socmint/templates/command_center.html").read_text()

    expected_links = {
        "/review/normalization-queue",
        "/subjects/{{ subject.id }}/dossier/readiness",
        "/subjects/{{ subject.id }}/claim-evidence-ledger",
        "/api/v1/subjects/{{ subject.id }}/export-manifest-draft",
        "/spine/subjects/{{ subject.id }}/dossier",
    }

    missing = {link for link in expected_links if link not in template}
    assert missing == set()


def test_command_center_labels_v13_workflow_links():
    template = Path("src/socmint/templates/command_center.html").read_text()

    for label in ["Review Queue", "Readiness", "Ledger", "Manifest", "Full Dossier v2"]:
        assert label in template
