from src.socmint.dossier_export_gate import export_gate_decision
from src.socmint.export_blocker_demo_v13_40 import ALLOWED_CASE_ID
from src.socmint.export_blocker_demo_v13_40 import ALLOWED_SUBJECT_ID
from src.socmint.export_blocker_demo_v13_40 import DENIED_CASE_ID
from src.socmint.export_blocker_demo_v13_40 import DENIED_SUBJECT_ID
from src.socmint.export_blocker_demo_v13_40 import create_export_blocker_demo


def test_export_blocker_demo_creates_allowed_and_denied_exports(tmp_path):
    result = create_export_blocker_demo(root=tmp_path)

    allowed = export_gate_decision(ALLOWED_SUBJECT_ID, ALLOWED_CASE_ID, root=tmp_path)
    denied = export_gate_decision(DENIED_SUBJECT_ID, DENIED_CASE_ID, root=tmp_path)

    assert result["schema"] == "socmint.export_blocker_demo.v13_40"
    assert result["allowed"]["ui_path"].startswith("/dossier/export-blockers")
    assert allowed["decision"] == "allow"
    assert denied["decision"] == "deny"
    assert "audit_coverage" in denied["blockers"]
