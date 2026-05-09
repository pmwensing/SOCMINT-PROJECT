import os
import sys
from pathlib import Path


os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
os.environ.setdefault("SOCMINT_CONNECTOR_DRY_RUN", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

for path in (PROJECT_ROOT, SRC_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
