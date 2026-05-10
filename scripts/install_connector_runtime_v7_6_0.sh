#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${SOCMINT_CONNECTOR_TOOLS_DIR:-$ROOT/.connector-tools}"
VENV="$TOOLS_DIR/venv"
BIN_DIR="$TOOLS_DIR/bin"
REPORT="$TOOLS_DIR/connector_runtime_install_report.json"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$TOOLS_DIR" "$BIN_DIR"

log() { printf '[+] %s\n' "$*"; }
warn() { printf '[!] %s\n' "$*" >&2; }

log "SOCMINT connector runtime installer v7.6.0"
log "Root: $ROOT"
log "Tools dir: $TOOLS_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  warn "Python not found: $PYTHON_BIN"
  exit 1
fi

log "Create/update isolated connector venv"
"$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip wheel setuptools

install_py_pkg() {
  local name="$1"
  local pkg="$2"
  log "Install $name via pip package: $pkg"
  if "$VENV/bin/python" -m pip install --upgrade "$pkg"; then
    echo "ok" > "$TOOLS_DIR/$name.install_status"
  else
    warn "$name install failed; continuing so health can report missing/failed"
    echo "failed" > "$TOOLS_DIR/$name.install_status"
  fi
}

install_py_pkg maigret maigret
install_py_pkg sherlock sherlock-project
install_py_pkg socialscan socialscan
install_py_pkg holehe holehe
install_py_pkg h8mail h8mail

cat > "$BIN_DIR/socmint-connectors-env" <<EOF
# Source this file before running SOCMINT connector health locally.
export PATH="$VENV/bin:$BIN_DIR:\$PATH"
export SOCMINT_CONNECTOR_TOOLS_DIR="$TOOLS_DIR"
EOF

cat > "$TOOLS_DIR/phoneinfoga_INSTALL.txt" <<'EOF'
PhoneInfoga is distributed as a separate binary. Install it manually for your platform, then put `phoneinfoga` on PATH.
Suggested check:
  phoneinfoga version || phoneinfoga --help
EOF

cat > "$TOOLS_DIR/archivebox_INSTALL.txt" <<'EOF'
ArchiveBox can be installed with pip or the project-supported install method for your OS.
After install, enable real captures explicitly:
  export SOCMINT_ARCHIVEBOX_ENABLED=true
Optional data dir:
  export SOCMINT_ARCHIVEBOX_DIR=/path/to/archivebox-data
Suggested check:
  archivebox version || archivebox --version
EOF

log "Write install report"
"$VENV/bin/python" - <<PY
import json, shutil, subprocess, os
from pathlib import Path
venv = Path("$VENV")
items = {}
checks = {
    "maigret": [str(venv / "bin" / "python"), "-m", "maigret", "--version"],
    "sherlock": [str(venv / "bin" / "sherlock"), "--version"],
    "socialscan": [str(venv / "bin" / "socialscan"), "--version"],
    "holehe": [str(venv / "bin" / "holehe"), "--version"],
    "h8mail": [str(venv / "bin" / "h8mail"), "--version"],
}
for name, cmd in checks.items():
    exe = cmd[0]
    exists = Path(exe).exists() or (name == "maigret" and Path(cmd[0]).exists())
    result = {"installed_path": exe if exists else None, "check_command": cmd, "available": False, "version": None, "error": None}
    if exists:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
            out = (proc.stdout or proc.stderr or "").strip().splitlines()
            result.update({"available": proc.returncode == 0, "returncode": proc.returncode, "version": out[0] if out else None})
        except Exception as exc:
            result["error"] = str(exc)
    items[name] = result
items["phoneinfoga"] = {"available": shutil.which("phoneinfoga") is not None, "installed_path": shutil.which("phoneinfoga"), "manual_install": True}
items["archivebox"] = {"available": shutil.which("archivebox") is not None, "installed_path": shutil.which("archivebox"), "enabled_env": os.environ.get("SOCMINT_ARCHIVEBOX_ENABLED")}
report = {"schema": "socmint.connector_runtime_install.v7_6_0", "tools_dir": "$TOOLS_DIR", "venv": "$VENV", "env_file": "$BIN_DIR/socmint-connectors-env", "items": items}
Path("$REPORT").write_text(json.dumps(report, indent=2, sort_keys=True))
print(json.dumps(report, indent=2, sort_keys=True))
PY

log "Done"
log "To activate in this shell: source $BIN_DIR/socmint-connectors-env"
log "Then run: make connectors-health"
