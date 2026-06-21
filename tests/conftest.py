import os
import sys
from pathlib import Path

import pytest


os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
os.environ.setdefault("SOCMINT_CONNECTOR_DRY_RUN", "1")
os.environ.setdefault("SOCMINT_SECRET_KEY", "test-secret-key-with-enough-entropy")
os.environ.setdefault("SOCMINT_DATA_DIR", "/tmp/socmint-pytest")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/socmint-pytest/socmint.db")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for path in (PROJECT_ROOT, SRC_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


@pytest.fixture(autouse=True)
def isolate_v31_0_workspace_append_only_inventories(request, monkeypatch):
    if request.node.path.name != "test_v31_0_publication_review_workspace.py":
        return
    from src.socmint import publication_review_workspace_v31_0 as workspace

    monkeypatch.setattr(workspace, "current_draft_revisions", lambda: [])
    monkeypatch.setattr(workspace, "current_editorial_validations", lambda: [])
    monkeypatch.setattr(workspace, "current_release_approvals", lambda: [])
    monkeypatch.setattr(workspace, "current_published_revisions", lambda: [])
