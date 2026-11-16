import asyncio
import json
from pathlib import Path

import pytest
import yaml
from test_config import write_config
from test_doctor import Upstream
from test_doctor import configured as doctor_configured
from test_doctor import settings as platform_settings
from test_doctor import workspace as scan_workspace
from test_scan import client_factory
from test_scan import upstream as scan_upstream
from typer.testing import CliRunner

from dce.cli import app
from dce.mcp_server import Runtime, create_server

settings = platform_settings
workspace = scan_workspace
configured = doctor_configured
upstream = scan_upstream


def test_status_reports_existing_run_and_record_facts(tmp_path):
    write_config(tmp_path, yaml.safe_load(Path('examples/dce.example.yaml').read_text()))
    directory = tmp_path / '.dce/runs'
    directory.mkdir()
    run = {
        'run_id': 'demo-run', 'updated_at': '2026-11-16T12:00:00+08:00', 'stage': 'verified',
        'bugs': [{'id': 4336, 'title': 'demo bug', 'opened_at': '2026-11-15',
                  'severity': 2, 'pri': 2}],
        'merges': {'demo-cloud': {'merged_at': '2026-11-16T11:00:00+08:00'}},
        'plan': {'commits': {'demo-cloud': [{'sha': 'abc1234', 'subject': 'fix: demo bug#4336',
                                          'bugs': [4336]}]}},
        'verifications': {'4336': {'at': '2026-11-16T12:00:00+08:00', 'evidence': []}},
        'events': [{'detail': 'demo'}] * 60,
    }
    (directory / 'demo-run.json').write_text(json.dumps(run))
    runtime = Runtime(workspace=tmp_path)
    result = runtime.call('dce_status', run_id='demo-run')
    assert result['ok'] and result['data']['runs'][0]['bugs'] == [4336]
    assert result['data']['record_facts'][0]['fixed_at'] == '2026-11-16T11:00:00+08:00'
    assert result['data']['record_facts'][0]['commits'] == ['abc1234 fix: demo bug#4336']
    assert runtime.call('dce_status', run_id='../demo')['error']['code'] == 'OUT_OF_SCOPE'
    assert runtime.call('dce_status', run_id='demo-missing')['error']['code'] == 'NOT_FOUND'


def test_setup_check_and_cli_share_json(configured, monkeypatch):
    root, settings = configured
    monkeypatch.setattr('dce.workspace.doctor.PlatformClient', client_factory(Upstream()))
    monkeypatch.setattr('dce.mcp_server.load_settings', lambda *args: settings)
    runtime = Runtime(workspace=root)
    expected = runtime.call('project_setup', action='check')
    assert expected['ok'] and expected['data']['passed']
    runner = CliRunner()
    result = runner.invoke(app, ['--workspace', str(root), 'setup', 'check'])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == expected
    result = runner.invoke(app, ['--workspace', str(root), '--pretty', 'status'])
    assert result.exit_code == 0 and 'demo-platform' in result.stdout


def test_setup_scan_returns_contract_summary(workspace, settings, upstream, monkeypatch):
    monkeypatch.setattr('dce.workspace.scan.PlatformClient', client_factory(upstream))
    monkeypatch.setattr('dce.mcp_server.load_settings', lambda *args: settings)
    result = Runtime(workspace=workspace).call('project_setup', action='scan')
    assert result['ok'] and result['data']['written'] == '.dce/dce.yaml'
    assert 'TODO(确认)' in result['summary'] and '| demo-cloud |' in result['summary']


def test_runtime_structured_errors_and_redacted_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr('dce.mcp_server.load_settings', lambda *args: (_ for _ in ()).throw(
        RuntimeError('Authorization: Bearer demo-secret')
    ))
    result = Runtime(workspace=tmp_path).call('project_setup', action='scan')
    assert result['error']['code'] == 'INTERNAL'
    assert 'RuntimeError' in result['error']['message']
    assert 'demo-secret' not in json.dumps(result) + capsys.readouterr().err


def test_fastmcp_implemented_tools_keep_matching_content(configured, monkeypatch):
    root, settings = configured
    monkeypatch.setattr('dce.workspace.doctor.PlatformClient', client_factory(Upstream()))
    monkeypatch.setattr('dce.mcp_server.load_settings', lambda *args: settings)

    async def exercise():
        result = await create_server(workspace=root).call_tool('project_setup', {'action': 'check'})
        assert json.loads(result.content[0].text) == result.structuredContent

    asyncio.run(exercise())


def test_status_bad_run_json_and_symlink_are_specific(tmp_path):
    write_config(tmp_path, yaml.safe_load(Path('examples/dce.example.yaml').read_text()))
    runs = tmp_path / '.dce/runs'
    runs.mkdir()
    (runs / 'demo-bad.json').write_text('{')
    result = Runtime(workspace=tmp_path).call('dce_status')
    assert result['error']['code'] == 'CONFIG_INVALID'
    assert 'demo-bad.json' in result['error']['message']
    (runs / 'demo-bad.json').unlink()
    (runs / 'demo-link.json').symlink_to(tmp_path.parent / 'demo-outside.json')
    result = Runtime(workspace=tmp_path).call('dce_status', run_id='demo-link')
    assert result['error']['code'] == 'OUT_OF_SCOPE'


@pytest.mark.parametrize('kwargs', [{'workspace': Path('relative')}, {}])
def test_cli_workspace_errors_are_json(tmp_path, monkeypatch, kwargs):
    monkeypatch.chdir(tmp_path)
    result = Runtime(**kwargs).call('dce_status')
    assert result['error']['code'] == 'WORKSPACE_REQUIRED'
