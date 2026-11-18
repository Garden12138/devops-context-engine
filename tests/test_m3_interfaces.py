import asyncio
import json

import pytest
from test_build import setup as build_setup
from test_merge import setup as merge_setup
from test_platform_migration import client
from typer.testing import CliRunner

from dce.cli import app
from dce.loop.runs import load_run
from dce.mcp_server import Runtime, create_server
from dce.settings import Settings
from dce.workspace.config import dump_config

build_setup = build_setup
merge_setup = merge_setup


def test_merge_runtime_rejection_and_mcp_success_without_credentials(merge_setup):
    ws, cfg, repo, run, f, calls = merge_setup
    (ws / '.dce/dce.yaml').write_text(dump_config(cfg))
    runtime = Runtime(workspace=ws, credentials=ws / 'missing.env')
    rejected = runtime.call('merge_to_test', run_id=run['run_id'])
    assert rejected['ok'] and rejected['data']['results'][0]['status'] == 'rejected'
    assert '先处理' in rejected['next']

    async def exercise():
        server = create_server(workspace=ws, credentials=ws / 'missing.env')
        result = await server.call_tool('merge_to_test', {
            'run_id': run['run_id'], 'approved_by_user': True})
        assert json.loads(result.content[0].text) == result.structuredContent
        assert result.structuredContent['data']['results'][0]['status'] == 'merged'

    asyncio.run(exercise())
    assert load_run(ws, run['run_id'])['stage'] == 'merged'
    runner = CliRunner()
    result = runner.invoke(app, ['--workspace', str(ws), 'merge', '--run', run['run_id'], '--yes'])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['data']['results'][0]['status'] == 'already_merged'


def test_merge_repositories_report_independently(merge_setup):
    ws, cfg, repo, run, f, calls = merge_setup
    (ws / '.dce/dce.yaml').write_text(dump_config(cfg))
    result = Runtime(workspace=ws).call('merge_to_test', run_id=run['run_id'],
                                      repos=['demo-unplanned', repo.name], approved_by_user=True)
    assert result['ok']
    assert [r['status'] for r in result['data']['results']] == ['rejected', 'merged']


@pytest.fixture
def build_runtime(build_setup, monkeypatch):
    ws, cfg, run, clock, server, gitlab = build_setup
    (ws / '.dce/dce.yaml').write_text(dump_config(cfg))
    settings = Settings(gitlab=gitlab.reader.config)
    monkeypatch.setattr('dce.mcp_server.load_settings', lambda *args: settings)
    monkeypatch.setattr('dce.mcp_server.PlatformClient', lambda *args: client(server.handle))
    return build_setup


def test_build_mcp_cli_and_status_only_gets(build_runtime):
    ws, cfg, run, clock, server, gitlab = build_runtime

    async def exercise():
        mcp = create_server(workspace=ws)
        result = await mcp.call_tool('ci_build', {'run_id': run['run_id']})
        assert json.loads(result.content[0].text) == result.structuredContent
        assert result.structuredContent['data']['items'][0]['compile']['action'] == 'played'
        server.calls.clear()
        result = await mcp.call_tool('ci_status', {'run_id': run['run_id'], 'wait_seconds': 0})
        assert json.loads(result.content[0].text) == result.structuredContent
        assert result.structuredContent['data']['overall'] == 'building'
        assert all(r.method == 'GET' for r in server.calls)

    asyncio.run(exercise())
    runner = CliRunner()
    prefix = ['--workspace', str(ws)]
    result = runner.invoke(app, [*prefix, 'build', '--run', run['run_id']])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['data']['items'][0]['compile']['action'] == 'already_running'
    server.calls.clear()
    result = runner.invoke(app, [*prefix, 'build-status', '--run', run['run_id'], '--wait', '0'])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['data']['overall'] == 'building'
    assert all(r.method == 'GET' for r in server.calls)


def test_cli_segments_long_wait_and_passes_retry_flag(monkeypatch):
    clock = [0]
    calls = []

    def call(self, tool, **kwargs):
        calls.append((tool, kwargs))
        clock[0] += kwargs.get('wait_seconds', 0)
        return {'ok': True, 'summary': 'demo CI', 'data': {'overall': 'building', 'items': []}}

    monkeypatch.setattr(Runtime, 'call', call)
    monkeypatch.setattr('dce.cli.time.monotonic', lambda: clock[0])
    runner = CliRunner()
    result = runner.invoke(app, ['build-status', '--run', 'demo-run', '--wait', '96'])
    assert result.exit_code == 0, result.output
    assert [args['wait_seconds'] for _, args in calls] == [45, 45, 6]
    calls.clear()
    result = runner.invoke(app, ['build', '--run', 'demo-run', '--retry-failed'])
    assert result.exit_code == 0
    assert calls == [('ci_build', {'run_id': 'demo-run', 'retry_failed': True})]


def test_merge_without_planned_repositories_is_rejected(merge_setup):
    from dce.loop.runs import save_run

    ws, cfg, repo, run, f, calls = merge_setup
    run['plan'] = {}
    save_run(ws, run)
    (ws / '.dce/dce.yaml').write_text(dump_config(cfg))
    result = Runtime(workspace=ws).call('merge_to_test', run_id=run['run_id'],
                                      approved_by_user=True)
    assert result['error']['code'] == 'PRECONDITION_FAILED'
    assert calls == []
