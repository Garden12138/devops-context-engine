import base64
import json
from copy import deepcopy

import httpx
import pytest
from test_platform_migration import client

from dce.errors import DceError, ErrorCode
from dce.platforms.portainer import Portainer


@pytest.mark.parametrize('status', [204, 404, 405])
@pytest.mark.parametrize('registry', [2, None])
def test_force_update_body_auth_and_compatibility_status(status, registry):
    calls = []

    def handle(req):
        calls.append(req)
        assert req.method == 'PUT'
        assert req.url.path == '/api/endpoints/1/forceupdateservice'
        assert json.loads(req.content) == {'ServiceID': 'demo1', 'PullImage': True}
        assert req.headers['X-API-Key'] == 'synthetic'
        if registry is None:
            assert 'X-Registry-Auth' not in req.headers
        else:
            assert json.loads(base64.b64decode(req.headers['X-Registry-Auth'])) == {'registryId': 2}
        return httpx.Response(status)

    with client(handle) as http:
        assert Portainer(http).force_update(1, 'demo1', registry) == status
    assert len(calls) == 1


@pytest.mark.parametrize('status,code', [(401, ErrorCode.AUTH_FAILED),
                                       (403, ErrorCode.PERMISSION_DENIED),
                                       (409, ErrorCode.PLATFORM_ERROR),
                                       (502, ErrorCode.PLATFORM_ERROR)])
def test_force_update_other_errors_are_specific_and_not_retried(status, code):
    calls = []

    def handle(req):
        calls.append(req)
        return httpx.Response(status)

    with client(handle) as http:
        http.settings.max_retries = 2
        with pytest.raises(DceError) as exc:
            Portainer(http).force_update(1, 'demo1', 2)
        assert exc.value.code == code
        assert f'HTTP {status}' in exc.value.message
        assert 'forceupdateservice' in exc.value.message and exc.value.hint
    assert len(calls) == 1


@pytest.mark.parametrize('force', [None, 7])
def test_docker_update_copies_spec_increments_force_and_unpins_digest(force):
    spec = {'Name': 'demo_test_demo-web', 'TaskTemplate': {'ContainerSpec': {
        'Image': 'registry.example.invalid:5000/demo/demo-web:dev@sha256:' + 'a' * 64,
        'Env': ['DEMO_MODE=test']}}}
    if force is not None:
        spec['TaskTemplate']['ForceUpdate'] = force
    original = deepcopy(spec)

    def handle(req):
        assert req.method == 'POST'
        assert req.url.path == '/api/endpoints/1/docker/services/demo1/update'
        assert req.url.params['version'] == '120'
        body = json.loads(req.content)
        assert body['TaskTemplate']['ForceUpdate'] == (force or 0) + 1
        assert body['TaskTemplate']['ContainerSpec']['Image'] == (
            'registry.example.invalid:5000/demo/demo-web:dev')
        assert body['TaskTemplate']['ContainerSpec']['Env'] == ['DEMO_MODE=test']
        assert json.loads(base64.b64decode(req.headers['X-Registry-Auth'])) == {'registryId': 2}
        return httpx.Response(200, json={})

    with client(handle) as http:
        Portainer(http).docker_update(1, 'demo1', 120, spec, 2)
    assert spec == original


def test_tasks_filters_exact_service_id():
    def handle(req):
        assert req.method == 'GET' and req.url.path == '/api/endpoints/1/docker/tasks'
        assert json.loads(req.url.params['filters']) == {'service': ['demo1']}
        return httpx.Response(200, json=[{'ID': 'demotask1', 'Status': {'State': 'running'}}])

    with client(handle) as http:
        assert Portainer(http).tasks(1, 'demo1')[0]['ID'] == 'demotask1'


@pytest.mark.parametrize('tty', [True, False])
def test_logs_since_decodes_frames_and_redacts(tty):
    text = b'2026-11-18T02:00:01Z demo synthetic\n'
    framed = b'\x01\0\0\0' + len(text).to_bytes(4, 'big') + text

    def handle(req):
        assert req.method == 'GET'
        if req.url.path.endswith('/logs'):
            assert req.url.path == '/api/endpoints/1/docker/services/demo1/logs'
            assert dict(req.url.params) == {'since': '1794967200', 'tail': '50',
                                            'stdout': '1', 'stderr': '1', 'timestamps': '1'}
            return httpx.Response(200, content=text if tty else framed)
        return httpx.Response(200, json={'Spec': {'TaskTemplate': {'ContainerSpec': {'TTY': tty}}}})

    with client(handle) as http:
        lines = Portainer(http).service_logs_since(1, 'demo1', '2026-11-18T02:00:00Z', 50)
    assert len(lines) == 1 and 'synthetic' not in lines[0] and 'demo' in lines[0]


def test_logs_tail_bounds_rejected_before_http():
    with client(lambda req: pytest.fail('invalid tail must not send HTTP')) as http:
        with pytest.raises(DceError) as exc:
            Portainer(http).service_logs_since(1, 'demo1', None, 301)
        assert exc.value.code == ErrorCode.CONFIG_INVALID


def test_corrupt_log_frames_report_service_and_response_status():
    def handle(req):
        return (httpx.Response(200, content=b'invalid frame') if req.url.path.endswith('/logs')
                else httpx.Response(200, json={'Spec': {}}))

    with client(handle) as http:
        with pytest.raises(DceError, match='Portainer.*demo1.*HTTP 200') as exc:
            Portainer(http).service_logs_since(1, 'demo1', None, 50)
        assert exc.value.hint
