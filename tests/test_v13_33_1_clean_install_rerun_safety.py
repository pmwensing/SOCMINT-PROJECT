from pathlib import Path


def test_clean_install_script_uses_unique_default_work_root_and_force_guard():
    script = Path("scripts/clean_install_acceptance_v13_33.sh").read_text()

    assert "$(date -u +%Y%m%d%H%M%S)" in script
    assert "CLEAN_INSTALL_FORCE" in script
    assert "Refusing to delete existing WORK_ROOT" in script
    assert "Use a fresh WORK_ROOT or rerun with CLEAN_INSTALL_FORCE=1" in script


def test_clean_install_script_handles_stale_docker_owned_files():
    script = Path("scripts/clean_install_acceptance_v13_33.sh").read_text()

    assert "docker compose down --volumes --remove-orphans" in script
    assert "Normal cleanup failed" in script
    assert "sudo rm -rf" in script
    assert "Clean install acceptance complete" in script
