import httpx
import pytest
from pydantic import SecretStr

from dce.errors import DceError, ErrorCode
from dce.platforms.http import PlatformClient
from dce.settings import PlatformConfig, Settings

ROUTES = [
    ('zentao', 'POST', '/api.php/v1/tokens'),
    ('zentao', 'POST', '/api.php/v1/bugs/1/resolve'),
    ('gitlab', 'POST', '/api/v4/projects/1/jobs/2/play'),
    ('gitlab', 'POST', '/api/v4/projects/1/jobs/2/retry'),
    ('gitlab', 'POST', '/api/v4/projects/1/pipeline'),
    ('portainer', 'PUT', '/api/endpoints/1/forceupdateservice'),
    ('portainer', 'POST', '/api/endpoints/1/docker/services/demo1/update'),
]


def client(handler):
    return PlatformClient(
        PlatformConfig(instance_id='demo', base_url='https://api.example.invalid/zentao',
                       token=SecretStr('synthetic')),
        Settings(request_interval=0, max_retries=2),
        transport=httpx.MockTransport(handler), sleep=lambda _: None,
    )


@pytest.mark.parametrize('kind,method,path', ROUTES)
def test_seven_write_routes_preserve_body_and_headers(kind, method, path):
    calls = []

    def handle(request):
        calls.append(request)
        assert request.content == b'{"demo":true}'
        assert request.headers['X-Demo'] == 'yes'
        if path != '/api.php/v1/tokens':
            header = {'gitlab': 'PRIVATE-TOKEN', 'portainer': 'X-API-Key', 'zentao': 'Token'}
            assert request.headers[header[kind]] == 'synthetic'
        return httpx.Response(200, json={'id': 1})

    with client(handle) as http:
        response = getattr(http, method.lower())(
            path, kind=kind, json={'demo': True}, headers={'X-Demo': 'yes'},
        )
    assert response.status_code == 200 and len(calls) == 1


@pytest.mark.parametrize('kind,method,path', [
    ('gitlab', 'DELETE', '/api/v4/projects/1'),
    ('gitlab', 'PATCH', '/api/v4/projects/1'),
    ('gitlab', 'POST', '/api/v4/projects/1/merge_requests'),
    ('portainer', 'POST', '/api/endpoints/1/docker/containers/x/exec'),
    ('zentao', 'POST', '/api.php/v1/bugs/1/close'),
    ('gitlab', 'POST', '/api/v4/projects/demo/jobs/2/play'),
    ('gitlab', 'POST', '/api/v4/projects/1/jobs/2/play/'),
    ('gitlab', 'POST', '/api/v4/projects/1/jobs/2/play\n'),
    ('gitlab', 'POST', '/api.php/v1/tokens'),
    ('portainer', 'POST', '/api/endpoints/1/docker/services/../update'),
])
def test_denied_writes_never_reach_transport(kind, method, path):
    calls = []
    with client(lambda r: calls.append(r)) as http, pytest.raises(DceError) as exc:
        http._request(method, path, kind=kind)
    assert exc.value.code == ErrorCode.PERMISSION_DENIED
    assert kind in exc.value.message and method in exc.value.message
    assert calls == []


@pytest.mark.parametrize('transport_failure', [False, True])
def test_write_errors_are_never_retried(transport_failure):
    calls = []

    def handle(request):
        calls.append(request)
        if transport_failure:
            raise httpx.ConnectError('demo unreachable', request=request)
        return httpx.Response(502)

    with client(handle) as http, pytest.raises(DceError) as exc:
        http.post('/api/v4/projects/1/pipeline', json={'ref': 'develop'})
    assert len(calls) == 1 and not exc.value.retryable
    assert '/api/v4/projects/1/pipeline' in exc.value.message


def test_token_helper_uses_whitelist():
    with client(lambda r: httpx.Response(200, json={'token': 'synthetic'})) as http:
        assert http.zentao_token('demo-user', 'synthetic').json()['token'] == 'synthetic'
