import asyncio
import json

import pytest
from test_deploy import NEW
from test_deploy import setup as deploy_setup
from test_platform_migration import client
from typer.testing import CliRunner

from dce.cli import app
from dce.loop.runs import load_run, save_run
from dce.mcp_server import Runtime, create_server
from dce.settings import Settings
from dce.workspace.config import dump_config

deploy_setup = deploy_setup


@pytest.fixture
def deploy_runtime(deploy_setup, monkeypatch):
    ws, cfg, run, clock, server, portainer = deploy_setup
    (ws / '.dce/dce.yaml').write_text(dump_config(cfg))
    settings = Settings(portainer=portainer.reader.config)
    monkeypatch.setattr('dce.mcp_server.load_settings', lambda *args: settings)
    monkeypatch.setattr('dce.mcp_server.PlatformClient', lambda *args: client(server.handle))
    return deploy_setup


def test_deploy_mcp_and_status_match_both_content_formats(deploy_runtime):
    ws, cfg, run, clock, server, portainer = deploy_runtime

    async def exercise():
        mcp = create_server(workspace=ws)
        result = await mcp.call_tool('service_deploy', {
            'run_id': run['run_id'], 'items': ['demo-web:.']})
        assert json.loads(result.content[0].text) == result.structuredContent
        assert result.structuredContent['data']['services'][0]['status'] == 'update_requested'
        assert len(server.writes()) == 1
        server.calls.clear()
        result = await mcp.call_tool('service_status', {
            'run_id': run['run_id'], 'wait_seconds': 0, 'logs_tail': 50})
        assert json.loads(result.content[0].text) == result.structuredContent
        row, = result.structuredContent['data']['services']
        assert row['verdict'] == 'converged' and row['running_digest'] == NEW
        assert row['logs'] and 'synthetic' not in json.dumps(row)
        assert all(r.method == 'GET' for r in server.calls)
        result = await mcp.call_tool('service_status', {
            'service': 'demo_test_demo-web', 'wait_seconds': 0, 'logs_tail': 50})
        assert result.structuredContent['data']['services'][0]['logs']

    asyncio.run(exercise())
    assert load_run(ws, run['run_id'])['stage'] == 'deployed'


def test_cli_deploy_and_status_share_loop_result_and_only_read_on_status(deploy_runtime):
    ws, cfg, run, clock, server, portainer = deploy_runtime
    runner = CliRunner()
    prefix = ['--workspace', str(ws)]
    result = runner.invoke(app, [*prefix, 'deploy', '--run', run['run_id']])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['data']['services'][0]['method'] == 'forceupdateservice'
    server.calls.clear()
    result = runner.invoke(app, [*prefix, 'deploy-status', '--run', run['run_id'],
                                 '--wait', '0', '--logs', '100'])
    assert result.exit_code == 0, result.output
    row, = json.loads(result.stdout)['data']['services']
    assert row['verdict'] == 'converged' and 'synthetic' not in row['logs'][0]
    assert all(r.method == 'GET' for r in server.calls)
    result = runner.invoke(app, [*prefix, '--pretty', 'deploy-status', '--run', run['run_id']])
    assert result.exit_code == 0 and 'converged' in result.stdout


@pytest.mark.parametrize('arguments', [{}, {'run_id': 'demo-run', 'service': 'demo_test_demo-web'}])
def test_status_requires_exactly_one_selector_without_loading_credentials(tmp_path,
                                                                         monkeypatch, arguments):
    def unexpected(*args):
        pytest.fail('invalid selectors must be rejected before credentials or HTTP')

    monkeypatch.setattr('dce.mcp_server.load_settings', unexpected)
    result = Runtime(workspace=tmp_path).call('service_status', **arguments)
    assert result['error']['code'] == 'CONFIG_INVALID'
    assert 'run_id' in result['error']['message'] and 'service' in result['error']['message']


def test_runtime_all_skipped_error_and_cli_failure_no_writes(deploy_runtime):
    ws, cfg, run, clock, server, portainer = deploy_runtime
    run['builds']['demo-web:.']['build']['status'] = 'running'
    save_run(ws, run)
    result = Runtime(workspace=ws).call('service_deploy', run_id=run['run_id'])
    assert result['error']['code'] == 'PRECONDITION_FAILED'
    assert '构建未完成' in result['error']['message'] and not server.calls
    result = CliRunner().invoke(app, ['--workspace', str(ws), 'deploy', '--run', run['run_id']])
    assert result.exit_code == 1
    assert json.loads(result.stdout)['error']['code'] == 'PRECONDITION_FAILED'
    assert not server.writes()


def test_cli_segments_long_deploy_wait_and_stops_on_terminal_verdict(monkeypatch):
    clock = [0]
    calls = []
    verdict = ['updating']

    def call(self, tool, **kwargs):
        calls.append((tool, kwargs))
        clock[0] += kwargs.get('wait_seconds', 0)
        return {'ok': True, 'summary': 'demo deploy', 'data': {
            'services': [{'service': 'demo_test_demo-web', 'verdict': verdict[0]}]}}

    monkeypatch.setattr(Runtime, 'call', call)
    monkeypatch.setattr('dce.cli.time.monotonic', lambda: clock[0])
    runner = CliRunner()
    result = runner.invoke(app, ['deploy-status', '--run', 'demo-run', '--wait', '96',
                                 '--logs', '100'])
    assert result.exit_code == 0, result.output
    assert [args['wait_seconds'] for _, args in calls] == [45, 45, 6]
    assert all(tool == 'service_status' and args['logs_tail'] == 100 for tool, args in calls)
    for terminal in ['converged', 'failed', 'digest_unverified']:
        calls.clear()
        verdict[0] = terminal
        result = runner.invoke(app, ['deploy-status', '--run', 'demo-run', '--wait', '96'])
        assert result.exit_code == 0
        assert len(calls) == 1


def test_runtime_portainer_error_stays_specific_and_redacted(deploy_runtime):
    ws, cfg, run, clock, server, portainer = deploy_runtime
    server.force_status = 403
    result = Runtime(workspace=ws).call('service_deploy', run_id=run['run_id'])
    assert result['error']['code'] == 'PERMISSION_DENIED'
    assert 'HTTP 403' in result['error']['message']
    assert 'demo_test_demo-web' in result['error']['message']
    assert 'synthetic' not in json.dumps(result) and len(server.writes()) == 1
