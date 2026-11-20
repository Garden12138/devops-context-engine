import asyncio
import json
from pathlib import Path

import httpx
import pytest
import yaml
from test_bugs_read import bug
from test_config import write_config
from test_platform_migration import client
from typer.testing import CliRunner

from dce.cli import app
from dce.errors import DceError
from dce.loop.runs import load_run, new_run, save_run
from dce.mcp_server import Runtime, create_server
from dce.settings import Settings

REPO = 'demo-cloud'
SERVICE = 'demo_test_demo-modules-order'
DIGEST = 'sha256:' + '123456789abc' + '0' * 52


@pytest.fixture
def resolve_run(tmp_path, monkeypatch):
    cfg = yaml.safe_load(Path('examples/dce.example.yaml').read_text())
    write_config(tmp_path, cfg)
    run = new_run(tmp_path, [4336])
    run['bugs'][0]['opened_by'] = 'demo-stale'
    run['stage'] = 'recorded'
    run['feature_branches'][REPO] = 'feature/1.2.0'
    run['plan'] = {
        'commits': {REPO: [{'sha': 'abc1234' + '0' * 33, 'subject': 'fix: demo bug#4336',
                            'bugs': [4336]}]},
        'items': [{'repo': REPO, 'id': f'{REPO}:demo-order', 'bugs': [4336],
                   'services': [SERVICE]}],
    }
    run['merges'][REPO] = {'test_branch': 'develop_v2', 'merge_sha': 'def5678' + '0' * 33,
                           'merged_at': '2026-11-13T15:42:10+08:00'}
    run['deploys'][SERVICE] = {'running_digest': DIGEST}
    run['record'] = {'file': 'projects/demo/缺陷修复记录.md', 'commit': '9f8e7d6' + '0' * 33}
    run['verifications']['4336'] = {'result': 'passed', 'notes': 'demo 验证通过'}
    save_run(tmp_path, run)
    monkeypatch.setattr('dce.mcp_server.load_settings', lambda *args: Settings())
    monkeypatch.setattr(Settings, 'platform', lambda *args: None)
    return run, cfg


class Upstream:
    def __init__(self, monkeypatch, before='active', after='resolved', product=100, reject=0):
        self.calls = []
        self.body = None
        self.before, self.after, self.product, self.reject = before, after, product, reject
        monkeypatch.setattr('dce.mcp_server.PlatformClient', lambda *args: client(self.handle))

    def handle(self, request):
        self.calls.append((request.method, request.url.path))
        if request.method == 'POST':
            self.body = json.loads(request.content)
            if self.reject:
                return httpx.Response(self.reject, json={'error': 'invalid build synthetic'})
            return httpx.Response(204)
        return httpx.Response(200, json=bug(
            status=self.before if self.body is None else self.after, product=self.product,
            openedBy={'account': 'demo-live'},
        ))


@pytest.mark.parametrize('key', ['verifications', 'record'])
def test_local_preconditions_block_without_platform_calls(
    resolve_run, tmp_path, monkeypatch, key,
):
    run, _ = resolve_run
    run[key] = {}
    save_run(tmp_path, run)
    upstream = Upstream(monkeypatch)
    result = Runtime(workspace=tmp_path).call('bug_resolve', run_id=run['run_id'])
    assert result['data']['results'][0]['status'] == 'blocked'
    assert not upstream.calls


@pytest.mark.parametrize('before', ['resolved', 'closed', 'inactive'])
def test_skip_terminal_status_and_block_other_states(resolve_run, tmp_path, monkeypatch, before):
    run, _ = resolve_run
    upstream = Upstream(monkeypatch, before=before)
    result = Runtime(workspace=tmp_path).call('bug_resolve', run_id=run['run_id'])
    assert result['data']['results'][0]['status'] == (
        'skipped' if before in {'resolved', 'closed'} else 'blocked'
    )
    assert upstream.calls == [('GET', '/api.php/v1/bugs/4336')]


def test_resolve_mcp_body_and_reread_match_contract(resolve_run, tmp_path, monkeypatch, capsys):
    run, _ = resolve_run
    upstream = Upstream(monkeypatch)
    run['bugs'] = [{'id': 4336}]
    save_run(tmp_path, run)

    async def invoke():
        response = await create_server(workspace=tmp_path).call_tool(
            'bug_resolve', {'run_id': run['run_id'], 'comment': 'demo 追加说明'},
        )
        assert json.loads(response.content[0].text) == response.structuredContent
        return response.structuredContent

    payload = asyncio.run(invoke())
    assert payload['data']['results'] == [
        {'bug': 4336, 'status': 'resolved', 'assigned_to': 'demo-live'},
    ]
    assert upstream.calls == [
        ('GET', '/api.php/v1/bugs/4336'),
        ('POST', '/api.php/v1/bugs/4336/resolve'),
        ('GET', '/api.php/v1/bugs/4336'),
    ]
    assert upstream.body == {
        'resolution': 'fixed', 'resolvedBuild': 'trunk', 'assignedTo': 'demo-live',
        'comment': '<br>'.join([
            '已修复，测试环境验证通过。',
            '修复提交：demo-cloud feature/1.2.0 abc1234（fix: demo bug#4336）',
            '合入测试分支：develop_v2 def5678，2026-11-13 15:42',
            f'部署：{SERVICE} sha256:123456789abc…',
            '验证：demo 验证通过',
            '记录：projects/demo/缺陷修复记录.md（commit 9f8e7d6）',
            'demo 追加说明',
        ]),
    }
    saved = load_run(tmp_path, run['run_id'])
    assert saved['stage'] == 'resolved'
    assert saved['zentao']['4336']['action'] == 'resolved'
    audit = json.loads(capsys.readouterr().err)
    assert audit['tool'] == 'bug_resolve' and audit['result'] == 'ok'
    assert 'demo 追加说明' not in json.dumps(audit, ensure_ascii=False)


def test_configurable_assignee_and_build_available_in_cli(resolve_run, tmp_path, monkeypatch):
    run, cfg = resolve_run
    cfg['zentao']['resolve'].update(assign_to='qa02', resolved_build='35')
    write_config(tmp_path, cfg)
    upstream = Upstream(monkeypatch)
    result = CliRunner().invoke(app, ['--workspace', str(tmp_path), 'resolve',
                                     '--run', run['run_id'], '--bug', '4336'])
    assert result.exit_code == 0, result.output
    assert upstream.body['assignedTo'] == 'qa02'
    assert upstream.body['resolvedBuild'] == '35'


@pytest.mark.parametrize(('options', 'code', 'message', 'methods'), [
    ({'after': 'active'}, 'PLATFORM_ERROR', 'active', ['GET', 'POST', 'GET']),
    ({'reject': 400}, 'PLATFORM_ERROR', 'HTTP 400', ['GET', 'POST']),
    ({'reject': 403}, 'PLATFORM_ERROR', 'HTTP 403', ['GET', 'POST']),
    ({'product': {'id': 200}}, 'OUT_OF_SCOPE', '200', ['GET']),
])
def test_errors_are_specific_and_never_retry(resolve_run, tmp_path, monkeypatch,
                                             options, code, message, methods):
    run, _ = resolve_run
    upstream = Upstream(monkeypatch, **options)
    result = Runtime(workspace=tmp_path).call('bug_resolve', run_id=run['run_id'])
    assert result['error']['code'] == code
    assert message in result['error']['message'] and '4336' in result['error']['message']
    assert [method for method, _ in upstream.calls] == methods
    assert load_run(tmp_path, run['run_id'])['stage'] == 'recorded'
    if 'reject' in options:
        assert 'invalid build' in result['error']['message']
        assert 'synthetic' not in result['error']['message']
        for key in ('zentao.resolve.assign_to', 'zentao.resolve.resolved_build'):
            assert key in result['error']['hint']


@pytest.mark.parametrize('key', ['assign_to', 'resolved_build'])
@pytest.mark.parametrize('value', ['', 'demo account', 'demo\taccount'])
def test_resolve_config_rejects_empty_and_whitespace(resolve_run, tmp_path, key, value):
    _, cfg = resolve_run
    cfg['zentao']['resolve'][key] = value
    with pytest.raises(DceError) as exc:
        write_config(tmp_path, cfg)
    assert exc.value.code == 'CONFIG_INVALID'
    assert f'zentao.resolve.{key}' in exc.value.message
