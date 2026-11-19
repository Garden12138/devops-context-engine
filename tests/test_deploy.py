import base64
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
import yaml
from test_build import FakeClock
from test_platform_migration import client

from dce.errors import DceError, ErrorCode
from dce.loop.deploy import deploy, status
from dce.loop.runs import load_run, new_run, save_run
from dce.platforms.portainer import Portainer
from dce.workspace.config import DceConfig

OLD = 'sha256:' + 'a' * 64
NEW = 'sha256:' + 'b' * 64


class DeployServer:
    def __init__(self, cfg, clock):
        self.clock = clock
        self.calls = []
        self.force_status = 204
        self.swarm = cfg.environment.swarm_id
        self.change_at = None
        self.value = {'ID': 'demo1', 'Version': {'Index': 120},
                      'UpdatedAt': '2026-11-18T01:00:00Z', 'Spec': {
                          'Name': 'demo_test_demo-web',
                          'Labels': {'com.docker.stack.namespace': cfg.environment.stack},
                          'Mode': {'Replicated': {'Replicas': 1}},
                          'TaskTemplate': {'ForceUpdate': 7, 'ContainerSpec': {
                              'Image': 'registry.example.invalid:5000/demo/demo-web:dev@' + OLD}}}}
        self.tasks = [self.task()]
        self.logs = b'2026-11-18T02:00:00Z demo synthetic\n'

    @staticmethod
    def task(state='running', digest=NEW, **kwargs):
        return {'ID': 'demotask1', 'DesiredState': 'running', 'ServiceID': 'demo1',
                'Spec': {'ContainerSpec': {'Image': 'demo/demo-web:dev@' + digest}},
                'Status': {'State': state, **kwargs}}

    def handle(self, req):
        self.calls.append(req)
        path = req.url.path
        if path.endswith('/forceupdateservice'):
            return httpx.Response(self.force_status)
        if path.endswith('/update'):
            return httpx.Response(200)
        if path.endswith('/info'):
            return httpx.Response(200, json={'Swarm': {'Cluster': {'ID': self.swarm}}})
        if path.endswith('/tasks'):
            tasks = ([self.task()] if self.change_at is not None
                     and self.clock.seconds >= self.change_at else self.tasks)
            return httpx.Response(200, json=tasks)
        if path.endswith('/logs'):
            return httpx.Response(200, content=b'\x01\0\0\0'
                                  + len(self.logs).to_bytes(4, 'big') + self.logs)
        if '/services/' in path:
            return httpx.Response(200, json=self.value)
        raise AssertionError(f'unexpected request {req.method} {path}')

    def writes(self):
        return [r for r in self.calls if r.method != 'GET']


@pytest.fixture
def setup(tmp_path):
    cfg = DceConfig.model_validate(yaml.safe_load(Path('examples/dce.example.yaml').read_text()))
    cfg.repos = [cfg.repos[2]]
    item = {'id': 'demo-web:.', 'repo': 'demo-web', 'module': '.', 'kind': 'web',
            'compile_job': 'compile_demo_web', 'build_job': 'build_demo_web',
            'image': 'demo/demo-web', 'services': ['demo_test_demo-web']}
    run = new_run(tmp_path, [4336])
    run['plan'] = {'items': [item], 'order': [item['id']]}
    run['builds'][item['id']] = {
        'compile': {'status': 'success', 'started_at': '2026-11-18T01:00:00Z'},
        'build': {'status': 'success', 'finished_at': '2026-11-18T02:00:00Z', 'digest': NEW}}
    save_run(tmp_path, run)
    clock = FakeClock()
    server = DeployServer(cfg, clock)
    with client(server.handle) as http:
        yield tmp_path, cfg, run, clock, server, Portainer(http)


def do_deploy(setup, **kwargs):
    ws, cfg, run, clock, server, portainer = setup
    return deploy(ws, cfg, run, client=portainer, **kwargs)


def do_status(setup, wait_seconds=0, **kwargs):
    ws, cfg, run, clock, server, portainer = setup
    return status(ws, cfg, run, wait_seconds=wait_seconds, clock=clock, client=portainer, **kwargs)


@pytest.mark.parametrize('state', ['missing', 'created', 'pending', 'running', 'failed', 'manual'])
def test_unfinished_build_skipped_without_any_http_and_all_skipped_error(setup, state):
    run = setup[2]
    if state == 'missing':
        run['builds'] = {}
    else:
        run['builds']['demo-web:.']['build']['status'] = state
    with pytest.raises(DceError) as exc:
        do_deploy(setup)
    assert exc.value.code == ErrorCode.PRECONDITION_FAILED
    assert 'demo_test_demo-web' in exc.value.message and '构建未完成' in exc.value.message
    assert setup[4].calls == []
    saved = load_run(setup[0], run['run_id'])['deploys']['demo_test_demo-web']
    assert saved['status'] == 'skipped' and saved['reason'] == '构建未完成'


def test_old_build_skipped_even_with_success_status(setup):
    setup[2]['builds']['demo-web:.']['build']['finished_at'] = '2026-11-18T00:59:59Z'
    with pytest.raises(DceError, match='旧构建') as exc:
        do_deploy(setup)
    assert exc.value.code == ErrorCode.PRECONDITION_FAILED and not setup[4].calls


@pytest.mark.parametrize('field', ['swarm_id', 'namespace', 'image', 'service', 'endpoint'])
def test_guard_rejects_each_mismatch_before_write(setup, field):
    ws, cfg, run, clock, server, portainer = setup
    spec = server.value['Spec']
    if field == 'swarm_id':
        server.swarm = 'demo-other'
    elif field == 'namespace':
        spec['Labels']['com.docker.stack.namespace'] = 'demo_other'
    elif field == 'image':
        spec['TaskTemplate']['ContainerSpec']['Image'] = 'demo/demo-web-other:dev'
    elif field == 'service':
        spec['Name'] = 'demo_test_demo-other'
    else:
        cfg.portainer.endpoint = None
    with pytest.raises(DceError, match=field) as exc:
        do_deploy(setup)
    assert exc.value.code == ErrorCode.OUT_OF_SCOPE and not server.writes()


def test_deploy_forceupdate_records_before_and_audits(setup, capsys):
    result = do_deploy(setup)
    row, = result['data']['services']
    assert row == {'service': 'demo_test_demo-web', 'service_id': 'demo1',
                   'status': 'update_requested', 'before_digest': OLD,
                   'expected_digest': NEW, 'method': 'forceupdateservice'}
    req, = setup[4].writes()
    assert req.method == 'PUT' and req.url.path == '/api/endpoints/1/forceupdateservice'
    assert json.loads(req.content) == {'ServiceID': 'demo1', 'PullImage': True}
    assert json.loads(base64.b64decode(req.headers['X-Registry-Auth'])) == {'registryId': 2}
    saved = load_run(setup[0], setup[2]['run_id'])
    before = saved['deploys']['demo_test_demo-web']['before']
    assert before == {'digest': OLD, 'version': 120, 'updated_at': '2026-11-18T01:00:00Z'}
    assert saved['stage'] == 'deploying'
    assert saved['deploys']['demo_test_demo-web']['requested_at']
    assert saved['events'][-1]['action'] == 'forceupdateservice'
    assert 'forceupdateservice' in capsys.readouterr().err


@pytest.mark.parametrize('http_status', [404, 405])
def test_fallback_on_404_405_pins_build_digest_and_converges(setup, http_status):
    server = setup[4]
    server.force_status = http_status
    row, = do_deploy(setup)['data']['services']
    assert row['method'] == 'docker_update'
    put, post = server.writes()
    assert put.method == 'PUT' and post.method == 'POST'
    body = json.loads(post.content)
    assert body['TaskTemplate']['ForceUpdate'] == 8
    image = body['TaskTemplate']['ContainerSpec']['Image']
    assert image == 'registry.example.invalid:5000/demo/demo-web:dev@' + NEW
    assert post.url.params['version'] == '120'
    assert json.loads(base64.b64decode(post.headers['X-Registry-Auth'])) == {'registryId': 2}
    assert [e['action'] for e in setup[2]['events']] == ['forceupdateservice', 'docker_update']
    server.value['UpdateStatus'] = {'State': 'completed'}
    server.tasks[0]['Spec']['ContainerSpec']['Image'] = image
    checked, = do_status(setup)['data']['services']
    assert checked['verdict'] == 'converged'
    assert checked['running_digest'] == checked['expected_digest'] == NEW


@pytest.mark.parametrize('http_status', [403, 409, 500, 502])
def test_failed_update_never_falls_back_and_preserves_audit(setup, http_status):
    setup[4].force_status = http_status
    with pytest.raises(DceError, match=f'HTTP {http_status}') as exc:
        do_deploy(setup)
    assert 'demo_test_demo-web' in exc.value.message and 'demo1' in exc.value.message
    assert {403: 'access denied', 409: 'resource version conflict',
            500: 'platform internal error', 502: 'invalid upstream response'}[http_status] in (
                exc.value.message)
    assert len(setup[4].writes()) == 1
    saved = load_run(setup[0], setup[2]['run_id'])
    assert saved['events'][-1]['result'] == 'error'
    assert saved['deploys']['demo_test_demo-web']['before']['digest'] == OLD


def test_plan_order_partial_skip_and_no_wait_between_submissions(setup):
    ws, cfg, run, clock, server, portainer = setup
    first = run['plan']['items'][0]
    other = {**first, 'id': 'demo-web:demo-other', 'module': 'demo-other',
             'services': ['demo_test_demo-other']}
    third = {**first, 'id': 'demo-web:demo-last', 'module': 'demo-last',
             'services': ['demo_test_demo-last']}
    run['plan']['items'] = [first, other, third]
    run['plan']['order'] = [third['id'], other['id'], first['id']]
    cfg.repos[0].modules = [cfg.repos[0].modules[0].model_copy(
        update={'path': i['module'], 'services': i['services']}) for i in [first, other, third]]
    run['builds'][third['id']] = deepcopy(run['builds'][first['id']])
    actual = server.handle

    def handle(req):
        if '/services/' in req.url.path and req.method == 'GET':
            value = deepcopy(server.value)
            value['Spec']['Name'] = req.url.path.rsplit('/', 1)[-1]
            value['ID'] = 'demo2' if value['Spec']['Name'].endswith('demo-last') else 'demo1'
            server.calls.append(req)
            return httpx.Response(200, json=value)
        return actual(req)

    with client(handle) as http:
        result = deploy(ws, cfg, run, client=Portainer(http))
    assert [s['service'] for s in result['data']['services']] == [
        'demo_test_demo-last', 'demo_test_demo-other', 'demo_test_demo-web']
    assert [s['status'] for s in result['data']['services']] == [
        'update_requested', 'skipped', 'update_requested']
    assert len(server.writes()) == 2 and clock.sleeps == []
    assert [json.loads(r.content)['ServiceID'] for r in server.writes()] == ['demo2', 'demo1']
    assert not any(r.url.path.endswith('/tasks') for r in server.calls)


@pytest.mark.parametrize('field,value', [('image', 'demo/demo-other'),
                                        ('services', ['demo_test_demo-other'])])
def test_tampered_plan_rejected_against_current_config(setup, field, value):
    setup[2]['plan']['items'][0][field] = value
    with pytest.raises(DceError) as exc:
        do_deploy(setup)
    assert exc.value.code == ErrorCode.OUT_OF_SCOPE and not setup[4].writes()


def test_unknown_selection_rejected_and_library_only_not_deployed(setup):
    with pytest.raises(DceError, match='demo-unknown'):
        do_deploy(setup, items=['demo-unknown'])
    setup[2]['plan']['items'][0]['kind'] = 'library'
    with pytest.raises(DceError) as exc:
        do_deploy(setup)
    assert exc.value.code == ErrorCode.PRECONDITION_FAILED and not setup[4].calls


def test_converged_checks_task_digest_persists_verdict_and_only_reads_platform(setup):
    do_deploy(setup)
    setup[4].calls.clear()
    setup[4].value['UpdateStatus'] = {'State': 'completed'}
    row, = do_status(setup)['data']['services']
    assert row == {'service': 'demo_test_demo-web', 'verdict': 'converged', 'running': 1,
                   'desired': 1, 'running_digest': NEW, 'expected_digest': NEW,
                   'update_state': 'completed', 'task_errors': [], 'logs': None}
    assert all(r.method == 'GET' for r in setup[4].calls)
    assert setup[2]['stage'] == 'deployed'
    saved = load_run(setup[0], setup[2]['run_id'])['deploys']['demo_test_demo-web']
    assert saved['verdict'] == 'converged' and saved['running_digest'] == NEW


@pytest.mark.parametrize('timestamp_source', ['status', 'updated_at'])
def test_failed_tasks_from_before_request_do_not_block_current_deployment(setup, timestamp_source):
    do_deploy(setup)
    run, server = setup[2], setup[4]
    run['deploys']['demo_test_demo-web']['requested_at'] = '2026-11-19T02:00:00Z'
    server.value['UpdateStatus'] = {'State': 'completed'}
    old_task = server.task('failed', digest=OLD, Err='demo old failure')
    old_task.pop('DesiredState')
    before = '2026-11-19T09:59:59.999999999+08:00'
    if timestamp_source == 'status':
        old_task['Status']['Timestamp'] = before
        old_task['UpdatedAt'] = '2026-11-19T02:01:00Z'
    else:
        old_task['UpdatedAt'] = before
    server.tasks.append(old_task)
    server.calls.clear()
    row, = do_status(setup)['data']['services']
    assert row['verdict'] == 'converged' and row['task_errors'] == []
    assert not any(r.url.path.endswith('/logs') for r in server.calls)


def test_task_created_before_request_but_failing_during_deploy_is_reported(setup):
    do_deploy(setup)
    run, server = setup[2], setup[4]
    run['deploys']['demo_test_demo-web']['requested_at'] = '2026-11-19T02:00:00Z'
    server.value['UpdateStatus'] = {'State': 'completed'}
    failed = server.task('rejected', Timestamp='2026-11-19T02:00:00Z', Err='demo rejection')
    failed.update(DesiredState='shutdown', CreatedAt='2026-11-19T01:00:00Z')
    server.tasks.append(failed)
    row, = do_status(setup)['data']['services']
    assert row['verdict'] == 'failed'
    assert row['task_errors'] == ['demotask1: demo rejection']
    assert row['logs']


def test_completed_rollout_with_only_tag_is_digest_unverified(setup):
    do_deploy(setup)
    server = setup[4]
    server.value['UpdateStatus'] = {'State': 'completed'}
    server.value['Spec']['TaskTemplate']['ContainerSpec']['Image'] = 'demo/demo-web:dev@' + NEW
    server.tasks[0]['Spec']['ContainerSpec']['Image'] = 'demo/demo-web:dev'
    result = do_status(setup, wait_seconds=45)
    row, = result['data']['services']
    assert row['verdict'] == 'digest_unverified' and row['task_errors'] == []
    assert row['running_digest'] is None and row['expected_digest'] == NEW
    assert result['next'] == '继续浏览器验证，并在汇报中说明镜像 digest 未能自动核对'
    assert setup[3].sleeps == [] and setup[2]['stage'] == 'deploying'
    saved = load_run(setup[0], setup[2]['run_id'])['deploys']['demo_test_demo-web']
    assert saved['verdict'] == 'digest_unverified'


@pytest.mark.parametrize('mode', ['empty', 'pending', 'old_digest', 'missing_digest',
                                 'mixed_digest', 'missing_replica', 'rolling'])
def test_updating_until_all_expected_tasks_match_digest(setup, mode):
    do_deploy(setup)
    server = setup[4]
    if mode == 'empty':
        server.tasks = []
    elif mode == 'pending':
        server.tasks = [server.task('pending')]
    elif mode == 'old_digest':
        server.tasks = [server.task(digest=OLD)]
    elif mode == 'missing_digest':
        server.tasks[0]['Spec']['ContainerSpec']['Image'] = 'demo/demo-web:dev'
    elif mode in {'mixed_digest', 'missing_replica'}:
        server.value['Spec']['Mode']['Replicated']['Replicas'] = 2
        if mode == 'mixed_digest':
            server.tasks.append(server.task(digest=OLD))
    else:
        server.value['UpdateStatus'] = {'State': 'updating'}
    assert do_status(setup)['data']['services'][0]['verdict'] == 'updating'


@pytest.mark.parametrize('mode', ['rejected', 'failed', 'paused', 'rollback_started',
                                 'rollback_completed', 'rollback_paused'])
def test_failed_tasks_and_update_states_return_errors_and_recent_redacted_logs(setup, mode):
    do_deploy(setup)
    if mode in {'rejected', 'failed'}:
        setup[4].tasks = [setup[4].task(mode, Err='demo image pull failed synthetic')]
    else:
        setup[4].value['UpdateStatus'] = {'State': mode, 'Message': 'demo update failed synthetic'}
    row, = do_status(setup)['data']['services']
    assert row['verdict'] == 'failed'
    assert row['task_errors'] and 'synthetic' not in json.dumps(row)
    assert row['logs'] and 'demo' in row['logs'][0]


@pytest.mark.parametrize('digest,expected', [(NEW, 'digest_unverified'), (OLD, 'updating')])
def test_unknown_build_digest_requires_actual_digest_change(setup, digest, expected):
    setup[2]['builds']['demo-web:.']['build']['digest'] = None
    do_deploy(setup)
    setup[4].tasks = [setup[4].task(digest=digest)]
    result = do_status(setup)
    row, = result['data']['services']
    assert row['verdict'] == expected and row['expected_digest'] is None
    if expected == 'digest_unverified':
        assert result['next'] == '继续浏览器验证，并在汇报中说明镜像 digest 未能自动核对'
    assert setup[2]['stage'] == 'deploying'


def test_logs_since_request_time_redacted_and_capped(setup):
    do_deploy(setup)
    row, = do_status(setup, logs_tail=50)['data']['services']
    req = next(r for r in setup[4].calls if r.url.path.endswith('/logs'))
    assert req.url.params['tail'] == '50' and int(req.url.params['since']) > 0
    assert row['logs'] and 'synthetic' not in row['logs'][0]


def test_poll_uses_fake_clock_returns_on_change_and_never_writes(setup):
    do_deploy(setup)
    setup[4].calls.clear()
    setup[4].tasks = [setup[4].task('pending')]
    assert do_status(setup, 45)['data']['services'][0]['verdict'] == 'updating'
    assert setup[3].seconds == 45
    setup[4].change_at = 55
    assert do_status(setup, 45)['data']['services'][0]['verdict'] == 'converged'
    assert setup[3].seconds == 55 and not setup[4].writes()


def test_named_service_and_scope_checks_for_status_logs(setup):
    ws, cfg, run, clock, server, portainer = setup
    result = status(ws, cfg, 'demo_test_demo-web', logs_tail=50, clock=clock, client=portainer)
    assert result['data']['services'][0]['logs']
    assert not server.writes()
    with pytest.raises(DceError, match='service'):
        status(ws, cfg, 'demo_other_demo-web', logs_tail=50, client=portainer)
    server.value['Spec']['Labels']['com.docker.stack.namespace'] = 'demo_other'
    with pytest.raises(DceError, match='namespace'):
        status(ws, cfg, 'demo_test_demo-web', logs_tail=50, client=portainer)


@pytest.mark.parametrize('arguments', [{'wait_seconds': -1}, {'wait_seconds': 46},
                                      {'logs_tail': -1}, {'logs_tail': 301}])
def test_status_argument_bounds_before_http(setup, arguments):
    with pytest.raises(DceError) as exc:
        do_status(setup, **arguments)
    assert exc.value.code == ErrorCode.CONFIG_INVALID and not setup[4].calls


def test_status_skipped_service_does_not_mark_run_deployed(setup):
    setup[2]['deploys']['demo_test_demo-web'] = {'status': 'skipped', 'reason': '构建未完成'}
    assert do_status(setup)['data']['services'][0]['verdict'] == 'updating'
    assert setup[2]['stage'] != 'deployed' and not setup[4].writes()


def test_status_before_deploy_does_not_report_convergence(setup):
    assert do_status(setup)['data']['services'][0]['verdict'] == 'updating'
    assert setup[2]['stage'] != 'deployed'


def test_build_only_module_deploys_and_uses_plan_selection(setup):
    setup[1].repos[0].modules[0].compile_job = None
    setup[2]['plan']['items'][0]['compile_job'] = None
    del setup[2]['builds']['demo-web:.']['compile']
    assert do_deploy(setup, items=['demo-web:.'])['data']['services'][0]['status'] == (
        'update_requested')


def test_fallback_rechecks_endpoint_guard(setup):
    ws, cfg, run, clock, server, portainer = setup
    actual = server.handle

    def handle(req):
        response = actual(req)
        if req.method == 'PUT':
            cfg.portainer.endpoint = 999
            return httpx.Response(404)
        return response

    with client(handle) as http, pytest.raises(DceError, match='endpoint'):
        deploy(ws, cfg, run, client=Portainer(http))
    assert len(server.writes()) == 1


def test_fallback_write_failure_preserves_both_events(setup):
    ws, cfg, run, clock, server, portainer = setup
    server.force_status = 404
    actual = server.handle

    def handle(req):
        response = actual(req)
        return httpx.Response(409) if req.url.path.endswith('/update') else response

    with client(handle) as http, pytest.raises(DceError, match='HTTP 409'):
        deploy(ws, cfg, run, client=Portainer(http))
    assert [(e['action'], e['result']) for e in run['events']] == [
        ('forceupdateservice', 'fallback'), ('docker_update', 'error')]


@pytest.mark.parametrize('field', ['ID', 'Version'])
def test_missing_service_identity_or_version_is_specific_and_no_write(setup, field):
    del setup[4].value[field]
    with pytest.raises(DceError, match='Portainer service demo_test_demo-web HTTP 200'):
        do_deploy(setup)
    assert not setup[4].writes()


def test_status_global_service_counts_expected_tasks(setup):
    do_deploy(setup)
    setup[4].value['Spec']['Mode'] = {'Global': {}}
    assert do_status(setup)['data']['services'][0]['verdict'] == 'converged'
