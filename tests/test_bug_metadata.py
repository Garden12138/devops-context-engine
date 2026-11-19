from pathlib import Path

import httpx
import pytest
import yaml
from gitfixture import GitFixture
from test_bugs_read import bug
from test_config import write_config
from test_platform_migration import client

from dce.loop.runs import load_run, new_run, save_run
from dce.mcp_server import Runtime
from dce.settings import Settings


@pytest.fixture
def plan_runtime(tmp_path):
    fixture = GitFixture(tmp_path / 'demo-fixture')
    cfg = yaml.safe_load(Path('examples/dce.example.yaml').read_text())
    repo = next(repo for repo in cfg['repos'] if repo['name'] == 'demo-web')
    repo['path'] = str(fixture.work.relative_to(tmp_path))
    cfg['repos'] = [repo]
    write_config(tmp_path, cfg)
    fixture.commit('src/demo.js', 'demo fix', 'fix: demo bug#4336')
    return Runtime(workspace=tmp_path, credentials=tmp_path / 'missing.env',
                   connections=tmp_path / 'missing.toml')


def mock_zentao(monkeypatch, handler):
    monkeypatch.setattr('dce.mcp_server.load_settings', lambda *args: Settings())
    monkeypatch.setattr(Settings, 'platform', lambda *args: None)
    monkeypatch.setattr('dce.mcp_server.PlatformClient', lambda *args: client(handler))


def test_plan_persists_metadata_and_refresh_reads_only_missing(plan_runtime, tmp_path, monkeypatch):
    calls = []

    def handler(request):
        assert request.method == 'GET'
        bug_id = int(request.url.path.rsplit('/', 1)[1])
        calls.append(bug_id)
        return httpx.Response(200, json=bug(id=bug_id, severity=2, pri=3))

    mock_zentao(monkeypatch, handler)
    planned = plan_runtime.call('deploy_plan', bug_ids=[4336])
    run_id = planned['data']['run_id']
    expected = {'id': 4336, 'title': 'demo bug', 'severity': 2, 'pri': 3, 'status': 'active',
                'opened_by': 'tester01', 'opened_at': '2026-11-16 10:00'}
    assert load_run(tmp_path, run_id)['bugs'] == [expected]
    refreshed = plan_runtime.call('deploy_plan', bug_ids=[4336, 4327], run_id=run_id)
    assert refreshed['ok']
    assert load_run(tmp_path, run_id)['bugs'] == [expected, {**expected, 'id': 4327}]
    assert calls == [4336, 4327]


@pytest.mark.parametrize(('failure', 'reason'), [
    ('not_configured', '凭证文件'),
    (401, 'HTTP 401'),
    (500, 'HTTP 500'),
    ('network', 'connection failed'),
])
def test_metadata_failure_keeps_git_plan(plan_runtime, tmp_path, monkeypatch, failure, reason):
    def handler(request):
        if failure == 'network':
            raise httpx.ConnectError('demo offline', request=request)
        return httpx.Response(failure, json={'error': 'Unauthorized'})

    if failure != 'not_configured':
        mock_zentao(monkeypatch, handler)
    planned = plan_runtime.call('deploy_plan', bug_ids=[4336])
    assert planned['data']['items'][0]['repo'] == 'demo-web'
    assert load_run(tmp_path, planned['data']['run_id'])['bugs'] == [{'id': 4336}]
    warning, = [w for w in planned['warnings'] if w['code'] == 'BUG_METADATA_UNAVAILABLE']
    assert '4336' in warning['message'] and '禅道' in warning['message']
    assert reason in warning['message']


def test_foreign_product_does_not_create_or_replace_run(plan_runtime, tmp_path, monkeypatch):
    mock_zentao(monkeypatch, lambda request: httpx.Response(200, json=bug(product={'id': 200})))
    denied = plan_runtime.call('deploy_plan', bug_ids=[4336])
    assert denied['error']['code'] == 'OUT_OF_SCOPE'
    assert all(value in denied['error']['message'] for value in ('4336', '100', '200'))
    assert not list((tmp_path / '.dce/runs').glob('*.json'))
    original = new_run(tmp_path, [4336])
    save_run(tmp_path, original)
    denied = plan_runtime.call('deploy_plan', bug_ids=[4336], run_id=original['run_id'])
    assert denied['error']['code'] == 'OUT_OF_SCOPE'
    assert load_run(tmp_path, original['run_id']) == original


def test_status_is_local_with_latest_related_merge_and_missing_metadata(
    plan_runtime, tmp_path, monkeypatch,
):
    def fail_if_contacted(*args):
        pytest.fail('dce_status must stay offline')

    monkeypatch.setattr('dce.mcp_server.load_settings', fail_if_contacted)
    run = new_run(tmp_path, [4336, 4327])
    run['bugs'][1].update(title='demo issue', severity=2, pri=3, opened_at='2026-11-15 12:30')
    run['plan']['commits'] = {
        repo: [{'sha': 'abc1234', 'subject': 'fix: demo', 'bugs': [bug_id]}]
        for repo, bug_id in [('demo-web', 4336), ('demo-cloud', 4336), ('demo-common', 4327)]
    }
    run['merges'] = {
        'demo-web': {'merged_at': '2026-11-16T12:00:00+02:00'},
        'demo-cloud': {'merged_at': '2026-11-16T09:00:00-02:00'},
        'demo-common': {'merged_at': '2026-11-16T13:00:00+00:00'},
    }
    verified_at = '2026-11-18T11:00:00+08:00'
    run['verifications']['4336'] = {'at': verified_at, 'evidence': ['demo.png']}
    save_run(tmp_path, run)
    result = plan_runtime.call('dce_status', run_id=run['run_id'])
    fact, second = result['data']['record_facts']
    assert fact['fixed_at'] == '2026-11-16T09:00:00-02:00'
    assert fact['verified_at'] == verified_at and fact['evidence'] == ['demo.png']
    assert all(fact[field] is None for field in ('title', 'severity', 'pri', 'opened_at'))
    warning, = result['warnings']
    assert warning['code'] == 'BUG_METADATA_MISSING' and '4336' in warning['message']
    assert '4327' not in warning['message']
    assert 'bug_get(bug_id, images=false)' in warning['hint']
    assert second['title'] == 'demo issue'
