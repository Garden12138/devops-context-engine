import json
from pathlib import Path

import httpx
import pytest
import yaml
from test_platform_migration import client

from dce.errors import DceError, ErrorCode
from dce.loop.build import poll_builds, start_builds
from dce.loop.runs import load_run, new_run, save_run
from dce.platforms.gitlab import GitLab
from dce.workspace.config import DceConfig


class FakeClock:
    def __init__(self):
        self.seconds = 0
        self.sleeps = []

    def monotonic(self):
        return self.seconds

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.seconds += seconds


class CiServer:
    def __init__(self, clock):
        self.clock = clock
        self.calls = []
        self.available_at = 0
        self.missing = False
        self.still_missing = False
        self.trace = 'demo trace\ndigest: sha256:' + 'a' * 64 + '\ndigest: sha256:' + 'b' * 64
        self.jobs = [
            {'id': 1, 'name': 'compile_demo_web', 'status': 'manual'},
            {'id': 2, 'name': 'build_demo_web', 'status': 'created'},
            {'id': 3, 'name': 'compile_demo_other', 'status': 'manual'},
        ]
        self.change_at = None

    def handle(self, req):
        self.calls.append(req)
        path = req.url.path
        if path.endswith('/pipelines'):
            assert req.url.params['sha'] == 'demo-merge-sha'
            assert req.url.params['ref'] == 'develop'
            return httpx.Response(200, json=[] if self.clock.seconds < self.available_at
                                  else [{'id': 100, 'sha': 'demo-merge-sha', 'ref': 'develop'}])
        if path.endswith('/bridges'):
            return httpx.Response(200, json=[{'name': 'trigger_dev',
                                             'downstream_pipeline': {'id': 200}}])
        if path.endswith('/jobs'):
            assert req.url.params['per_page'] == '100'
            missing = self.still_missing or (self.missing and '/101/' not in path)
            jobs = [] if missing else self.jobs
            if self.change_at is not None and self.clock.seconds >= self.change_at:
                jobs = [{**j, 'status': 'success'} for j in jobs]
            return httpx.Response(200, json=jobs, headers={'X-Next-Page': ''})
        if path.endswith('/pipeline'):
            assert json.loads(req.content) == {'ref': 'develop'}
            return httpx.Response(201, json={'id': 101})
        if path.endswith(('/play', '/retry')):
            job = next(j for j in self.jobs if str(j['id']) == path.split('/')[-2])
            job['status'] = 'pending'
            return httpx.Response(200, json=job)
        if path.endswith('/trace'):
            return httpx.Response(200, text=self.trace)
        raise AssertionError(f'unexpected request {req.method} {path}')

    def writes(self):
        return [r.url.path for r in self.calls if r.method != 'GET']


@pytest.fixture
def setup(tmp_path):
    cfg = DceConfig.model_validate(yaml.safe_load(Path('examples/dce.example.yaml').read_text()))
    cfg.repos = [cfg.repos[2]]
    repo = cfg.repos[0]
    item = {'id': 'demo-web:.', 'repo': repo.name, 'module': '.', 'kind': 'web',
            'compile_job': 'compile_demo_web', 'build_job': 'build_demo_web',
            'image': 'demo/demo-web', 'services': ['demo_test_demo-web']}
    run = new_run(tmp_path, [4336])
    run['plan'] = {'items': [item], 'order': [item['id']]}
    run['merges'] = {repo.name: {'merge_sha': 'demo-merge-sha', 'test_branch': 'develop'}}
    save_run(tmp_path, run)
    clock = FakeClock()
    server = CiServer(clock)
    with client(server.handle) as http:
        yield tmp_path, cfg, run, clock, server, GitLab(http)


def start(setup, **kwargs):
    ws, cfg, run, clock, server, gitlab = setup
    return start_builds(ws, cfg, run, client=gitlab, clock=clock, **kwargs)


def poll(setup, wait=0):
    ws, cfg, run, clock, server, gitlab = setup
    return poll_builds(ws, cfg, run, wait, clock, client=gitlab)


def test_direct_only_plays_planned_compile_and_repeated_call_is_idle(setup):
    result = start(setup)
    assert result['data']['items'][0]['compile']['action'] == 'played'
    assert setup[4].writes() == ['/api/v4/projects/13/jobs/1/play']
    assert start(setup)['data']['items'][0]['compile']['action'] == 'already_running'
    assert len(setup[4].writes()) == 1
    assert load_run(setup[0], setup[2]['run_id'])['builds']['demo-web:.']['pipeline_id'] == 100


def test_child_pipeline(setup):
    setup[1].repos[0].ci.mode = 'child'
    setup[1].repos[0].ci.trigger_job = 'trigger_dev'
    row, = start(setup)['data']['items']
    assert row['pipeline_id'] == 100 and row['child_pipeline_id'] == 200
    assert any('/pipelines/200/jobs' in r.url.path for r in setup[4].calls)


def test_delayed_pipeline_uses_injected_clock(setup):
    setup[4].available_at = 10
    start(setup)
    assert setup[3].sleeps == [5, 5]


def test_pipeline_timeout_is_bounded(setup):
    setup[4].available_at = 50
    with pytest.raises(DceError) as exc:
        start(setup)
    assert exc.value.code == ErrorCode.TIMEOUT and setup[3].seconds == 45
    assert 'demo-merge-sha' in exc.value.message and not setup[4].writes()


def test_missing_job_creates_one_pipeline_and_reuses_across_calls(setup):
    setup[4].missing = True
    row, = start(setup)['data']['items']
    assert row['pipeline_id'] == 101
    assert row['compile']['action'] in {'played', 'created_pipeline'}
    setup[2].clear()
    setup[2].update(load_run(setup[0], setup[2].baseline['run_id']))
    start(setup)
    assert sum(p.endswith('/pipeline') for p in setup[4].writes()) == 1


def test_still_missing_never_creates_a_second_pipeline(setup):
    setup[4].still_missing = True
    for _ in range(2):
        with pytest.raises(DceError) as exc:
            start(setup)
        assert exc.value.code == ErrorCode.CI_JOB_MISSING
        assert '101' in exc.value.message and 'compile_demo_web' in exc.value.message
        assert '/pipelines/101' in exc.value.hint
    assert sum(p.endswith('/pipeline') for p in setup[4].writes()) == 1


@pytest.mark.parametrize('retry_failed,status', [(False, 'failed'), (True, 'failed'),
                                                (True, 'canceled')])
def test_retry_failed_compile_is_opt_in(setup, retry_failed, status):
    setup[4].jobs[0]['status'] = status
    start(setup, retry_failed=retry_failed)
    assert setup[4].writes() == (['/api/v4/projects/13/jobs/1/retry'] if retry_failed else [])


def test_manual_build_requires_another_start_and_poll_only_gets(setup):
    setup[4].jobs[0]['status'] = 'success'
    setup[4].jobs[1]['status'] = 'manual'
    row, = poll(setup)['data']['items']
    assert row['build']['status'] == 'manual'
    assert 'ci_build' in poll(setup)['next']
    assert all(r.method == 'GET' for r in setup[4].calls)
    start(setup)
    assert setup[4].writes() == ['/api/v4/projects/13/jobs/2/play']


def test_stale_success_is_not_built_and_start_retries_build(setup):
    compile, build = setup[4].jobs[:2]
    compile.update(status='success', started_at='2026-11-18T02:00:00Z')
    build.update(status='success', finished_at='2026-11-18T01:59:00Z')
    result = poll(setup)
    assert result['data']['overall'] == 'building' and setup[2]['stage'] == 'building'
    assert 'ci_build' in result['next'] and '旧构建' in result['next']
    assert not setup[4].writes()
    assert start(setup)['data']['items'][0]['build']['action'] == 'retried'


@pytest.mark.parametrize('trace,digest,warning', [
    ('digest: sha256:' + 'a' * 64 + '\ndigest: sha256:' + 'b' * 64, 'sha256:' + 'b' * 64, None),
    ('demo no digest', None, 'DIGEST_UNKNOWN'),
])
def test_success_digest_uses_last_match(setup, trace, digest, warning):
    for job in setup[4].jobs[:2]:
        job['status'] = 'success'
    setup[4].trace = trace
    result = poll(setup)
    assert result['data']['overall'] == 'succeeded' and setup[2]['stage'] == 'built'
    assert result['data']['items'][0]['build']['digest'] == digest
    if warning:
        assert result['warnings'][0]['code'] == warning
    assert all(r.method == 'GET' for r in setup[4].calls)


@pytest.mark.parametrize('trace,category', [
    ('Cannot connect to the Docker daemon', 'infrastructure'),
    ('TLS handshake timeout', 'infrastructure'), ('i/o timeout', 'infrastructure'),
    ('context deadline exceeded', 'infrastructure'),
    ('no basic auth credentials', 'infrastructure'),
    ('pull access denied', 'infrastructure'), ('toomanyrequests', 'infrastructure'),
    ('runner system failure', 'infrastructure'),
    ('ERROR: Job failed (system failure)', 'infrastructure'),
    ('no space left on device', 'infrastructure'), ('BUILD FAILURE', 'code'),
    ('COMPILATION ERROR', 'code'), ('npm ERR!', 'code'), ('ERR_PNPM', 'code'),
    ('error TS1234', 'code'), ('Module not found', 'code'), ('SyntaxError', 'code'),
    ('demo unexpected failure', 'unknown'),
])
def test_failure_classification_trace_tail_and_stage(setup, trace, category):
    setup[4].jobs[0]['status'] = 'failed'
    setup[4].trace = '\n'.join(['demo line'] * 100 + [trace, 'PRIVATE-TOKEN: synthetic'])
    result = poll(setup)
    assert result['data']['overall'] == 'failed'
    job = result['data']['items'][0]['compile']
    assert job['failure'] == category and len(job['trace_tail'].splitlines()) == 80
    assert 'synthetic' not in job['trace_tail']
    assert setup[2]['stage'] == ('fixing' if category == 'code' else 'building')
    assert all(r.method == 'GET' for r in setup[4].calls)


def test_poll_wait_45_and_early_change(setup):
    setup[4].jobs[0]['status'] = 'running'
    assert poll(setup, 45)['data']['overall'] == 'building'
    assert setup[3].seconds == 45
    setup[4].change_at = 55
    assert poll(setup, 45)['data']['overall'] == 'succeeded'
    assert setup[3].seconds == 55
    assert all(r.method == 'GET' for r in setup[4].calls)


def test_unplanned_selection_and_unmerged_repo_are_rejected(setup):
    with pytest.raises(DceError, match='demo-unknown'):
        start(setup, items=['demo-unknown'])
    setup[2]['merges'] = {}
    with pytest.raises(DceError) as exc:
        start(setup)
    assert exc.value.code == ErrorCode.PRECONDITION_FAILED
    assert setup[4].calls == []


def test_shared_compile_is_played_once_per_call(setup):
    item = setup[2]['plan']['items'][0]
    setup[2]['plan']['items'].append({**item, 'id': 'demo-web:demo-extra', 'module': 'demo-extra'})
    result = start(setup)
    assert len(result['data']['items']) == 2
    assert setup[4].writes() == ['/api/v4/projects/13/jobs/1/play']


@pytest.mark.parametrize('kind', ['library', 'build_only'])
def test_single_job_items(setup, kind):
    item = setup[2]['plan']['items'][0]
    if kind == 'library':
        item.update(kind='library', build_job=None)
        setup[4].jobs[0]['status'] = 'success'
    else:
        item['compile_job'] = None
        setup[4].jobs[1]['status'] = 'manual'
        start(setup)
        assert setup[4].writes() == ['/api/v4/projects/13/jobs/2/play']
        setup[4].jobs[1]['status'] = 'success'
    assert poll(setup)['data']['overall'] == 'succeeded'


@pytest.mark.parametrize('status', ['failed', 'canceled'])
def test_failed_build_retry_is_opt_in(setup, status):
    setup[4].jobs[0]['status'] = 'success'
    setup[4].jobs[1]['status'] = status
    start(setup)
    assert not setup[4].writes()
    start(setup, retry_failed=True)
    assert setup[4].writes() == ['/api/v4/projects/13/jobs/2/retry']


def test_project_guard_prevents_play_of_wrong_project_job(setup):
    setup[4].jobs[0]['project_id'] = 999
    with pytest.raises(DceError, match='project_id') as exc:
        start(setup)
    assert exc.value.code == ErrorCode.OUT_OF_SCOPE and not setup[4].writes()


def test_pipeline_creation_failure_is_audited_and_not_repeated(setup):
    server = setup[4]
    server.still_missing = True
    actual = server.handle

    def failing(req):
        if req.url.path.endswith('/pipeline'):
            server.calls.append(req)
            return httpx.Response(502)
        return actual(req)

    with client(failing) as http:
        local_setup = (*setup[:5], GitLab(http))
        with pytest.raises(DceError) as exc:
            start(local_setup)
        assert exc.value.code == ErrorCode.PLATFORM_ERROR
        with pytest.raises(DceError) as exc:
            start(local_setup)
        assert exc.value.code == ErrorCode.CI_JOB_MISSING
    assert sum(p.endswith('/pipeline') for p in server.writes()) == 1
    assert any(e['result'] == 'error' for e in setup[2]['events'])


def test_gitlab_jobs_all_paginates_with_page_size_100():
    pages = []

    def handle(req):
        assert req.method == 'GET' and req.url.params['per_page'] == '100'
        page = req.url.params['page']
        pages.append(page)
        return httpx.Response(200, json=[{'id': int(page)}],
                              headers={'X-Next-Page': '2' if page == '1' else ''})

    with client(handle) as http:
        http.settings.page_size = 1
        http.sleep = lambda _: None
        assert GitLab(http).jobs_all('13', '100') == [{'id': 1}, {'id': 2}]
    assert pages == ['1', '2']
