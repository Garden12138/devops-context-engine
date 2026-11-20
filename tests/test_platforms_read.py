import httpx
import pytest

from dce.errors import DceError
from dce.platforms.gitlab import GitLab
from dce.platforms.http import PlatformClient
from dce.platforms.portainer import Portainer
from dce.settings import PlatformConfig, Settings


@pytest.fixture
def settings():
    return Settings(**{
        platform: PlatformConfig(
            instance_id=platform, base_url=f'https://{platform}.example.invalid',
            token='demo-token',
        ) for platform in ('gitlab', 'portainer', 'zentao')
    }, request_interval=0, max_retries=0)


def test_gitlab_encoded_paths_and_queries(settings):
    received = []

    def handle(request):
        received.append(request)
        assert request.headers['PRIVATE-TOKEN'] == 'demo-token'
        if request.url.path.endswith('/raw'):
            assert request.url.params['ref'] == 'feature/demo'
            assert b'demo%2Fdev.yml' in request.url.raw_path
            return httpx.Response(200, text='demo-ci')
        if request.url.path.endswith('/branches'):
            assert request.url.params['search'] == 'develop'
            return httpx.Response(200, json=[{'name': 'develop'}])
        if request.url.path.endswith('/self'):
            return httpx.Response(200, json={'scopes': ['api']})
        assert b'demo%2Fdemo-cloud' in request.url.raw_path
        return httpx.Response(200, json={'id': 12})

    with PlatformClient(settings.gitlab, settings, transport=httpx.MockTransport(handle)) as reader:
        gitlab = GitLab(reader)
        assert gitlab.project_by_path('demo/demo-cloud')['id'] == 12
        assert list(gitlab.branches(12, 'develop')) == [{'name': 'develop'}]
        assert gitlab.raw_file('12', 'demo/dev.yml', 'feature/demo') == 'demo-ci'
        assert gitlab.token_self()['scopes'] == ['api']
    assert len(received) == 4


@pytest.mark.parametrize('status', [404, 403])
def test_token_self_only_404_is_optional(settings, status):
    with PlatformClient(settings.gitlab, settings, transport=httpx.MockTransport(
        lambda r: httpx.Response(status)
    )) as reader:
        if status == 404:
            assert GitLab(reader).token_self() is None
        else:
            with pytest.raises(DceError) as error:
                GitLab(reader).token_self()
            assert error.value.code == 'PERMISSION_DENIED'


def test_portainer_read_endpoints(settings):
    def handle(request):
        assert request.headers['X-API-Key'] == 'demo-token'
        data = {
            '/api/endpoints': [{'Id': 1, 'Type': 1}],
            '/api/stacks': [{'Id': 2, 'Name': 'demo_test'}],
            '/api/registries': [{'Id': 3, 'URL': 'registry.example.invalid:5000'}],
            '/api/endpoints/1/docker/info': {'Swarm': {'Cluster': {'ID': 'demo123'}}},
            '/api/endpoints/1/docker/services': [{'Spec': {'Name': 'demo_test_demo-web'}}],
        }[request.url.path]
        return httpx.Response(200, json=data)

    with PlatformClient(
        settings.portainer, settings, transport=httpx.MockTransport(handle),
    ) as reader:
        portainer = Portainer(reader)
        assert portainer.endpoints()[0]['Id'] == 1
        assert portainer.stacks()[0]['Name'] == 'demo_test'
        assert portainer.registries()[0]['Id'] == 3
        assert portainer.swarm_id(1) == 'demo123'
        assert portainer.services('1')[0]['Spec']['Name'] == 'demo_test_demo-web'


def test_missing_swarm_has_specific_error(settings):
    with PlatformClient(settings.portainer, settings, transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={'Swarm': {}})
    )) as reader:
        with pytest.raises(DceError, match='endpoint 1.*Swarm.Cluster.ID'):
            Portainer(reader).swarm_id(1)
