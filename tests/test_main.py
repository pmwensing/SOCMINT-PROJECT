import json
import sys
from unittest.mock import patch

import pytest

from src.socmint import main as socmint_main


def test_validate_target_rejects_shell_metacharacters():
    with pytest.raises(ValueError, match='Invalid characters'):
        socmint_main.validate_target('alice;whoami')


def test_detect_type_email_phone_and_username():
    assert socmint_main.detect_type('operator@example.com') == 'email'
    assert socmint_main.detect_type('+14155552671') == 'phone'
    assert socmint_main.detect_type('operator_1') == 'username'


def test_detect_type_rejects_invalid_target():
    with pytest.raises(ValueError, match='Invalid target format'):
        socmint_main.detect_type('bad target!')


@patch('src.socmint.main.run_recon_ng', return_value='ok')
@patch('src.socmint.main.run_spiderfoot', return_value='ok')
@patch('src.socmint.main.run_instaloader', return_value='ok')
@patch('src.socmint.main.run_social_analyzer', return_value='ok')
@patch('src.socmint.main.run_socialscan', return_value='ok')
@patch('src.socmint.main.run_maigret', return_value='ok')
@patch('src.socmint.main.run_sherlock', return_value='ok')
def test_build_dossier_username(mock_sherlock, *_):
    dossier = socmint_main.build_dossier('testuser', 'username')
    assert 'sherlock' in dossier['data']
    assert dossier['type'] == 'username'


@patch('src.socmint.main.run_recon_ng')
@patch('src.socmint.main.run_sherlock', return_value='ok')
def test_build_dossier_respects_enabled_tools(mock_sherlock, mock_recon_ng):
    dossier = socmint_main.build_dossier('testuser', 'username', enabled_tools={'sherlock'})
    assert dossier['data'] == {'sherlock': 'ok'}
    mock_sherlock.assert_called_once_with('testuser')
    mock_recon_ng.assert_not_called()


def test_retrieve_path_prints_existing_dossier(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['socmint', 'operator_1', '--retrieve'])
    monkeypatch.setattr(socmint_main, 'get_dossier', lambda target: {'target': target, 'data': {}})

    socmint_main.main()

    output = capsys.readouterr().out
    assert 'Retrieved dossier:' in output
    assert '"target": "operator_1"' in output


def test_main_handles_invalid_target(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['socmint', 'bad;target'])

    socmint_main.main()

    assert 'Error: Invalid characters in target.' in capsys.readouterr().out


def test_main_can_export_generated_dossier(monkeypatch, tmp_path, capsys):
    export_path = tmp_path / 'dossier.json'
    dossier = {'target': 'operator_1', 'type': 'username', 'data': {'sherlock': 'ok'}}
    monkeypatch.setattr(sys, 'argv', [
        'socmint',
        'operator_1',
        '--no-enrich',
        '--output-json',
        '--tools',
        'sherlock',
        '--export',
        str(export_path),
    ])
    monkeypatch.setattr(socmint_main, 'build_dossier', lambda *args, **kwargs: dossier)
    monkeypatch.setattr(socmint_main, 'save_dossier', lambda saved: None)

    socmint_main.main()

    assert json.loads(capsys.readouterr().out) == dossier
    assert json.loads(export_path.read_text()) == dossier


def test_init_admin_command_creates_admin(monkeypatch, tmp_path, capsys):
    from src.socmint import database as db

    monkeypatch.setattr(sys, 'argv', ['socmint', 'init-admin', 'admin', 'StrongAdmin123!'])
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{tmp_path / 'socmint-admin.db'}")
    monkeypatch.setenv('SOCMINT_DATA_DIR', str(tmp_path))

    socmint_main.main()

    assert 'Admin user created: admin' in capsys.readouterr().out
    assert db.get_user_by_username('admin').is_admin is True


def test_recon_ng_uses_temporary_script(monkeypatch):
    calls = {}

    def fake_run_command(command, tool_name):
        calls['command'] = command
        calls['tool_name'] = tool_name
        return 'ok'

    monkeypatch.setattr(socmint_main, 'run_command', fake_run_command)

    assert socmint_main.run_recon_ng('example.com') == 'ok'
    assert calls['tool_name'] == 'Recon-ng'
    assert calls['command'][0:2] == ['recon-ng', '-r']
    assert calls['command'][2] != '/tmp/recon_script'
