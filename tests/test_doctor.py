from pathlib import Path

import httpx
import pytest
import yaml
from test_platforms_read import settings as platform_settings
from test_scan import client_factory, git, service
from test_scan import workspace as scan_workspace

from dce.workspace.doctor import check

settings = platform_settings
workspace = scan_workspace


@pytest.fixture
def configured(workspace, settings):
    data = yaml.safe_load(Path('examples/dce.example.yaml').read_text())
    data['repos'] = data['repos'][1:]
    data['repos'][0]['test_branch'] = 'develop'
    data['zentao']['account'] = 'demo-dev'
    settings._zentao_account = 'demo-dev'
    (workspace / '.dce').mkdir()
    (workspace / '.dce/dce.yaml').write_text(yaml.safe_dump(data))
    return workspace, settings


class Upstream:
    def __init__(self, failure=None):
        self.failure = failure
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        assert request.method == 'GET'
        path = request.url.path
        if path.endswith('/products/100/bugs'):
            if self.failure in {'zentao.login', 'zentao.product'}:
                return httpx.Response(401 if self.failure == 'zentao.login' else 404)
            return httpx.Response(200, json={'bugs': []})
        if path == '/api/v4/user':
            return httpx.Response(401 if self.failure == 'gitlab.token' else 200,
                                  json={'id': 1})
        if path.endswith('/personal_access_tokens/self'):
            if self.failure == 'scope404':
                return httpx.Response(404)
            return httpx.Response(200, json={
                'scopes': ['read_api'] if self.failure == 'gitlab.token_scope' else ['api'],
            })
        if path.endswith('/repository/branches'):
            name = 'demo-cloud' if '/12/' in path else 'demo-web'
            branches = ([] if self.failure == f'repo.{name}.test_branch'
                        else [{'name': 'develop'}])
            return httpx.Response(200, json=branches)
        if path.endswith('/raw'):
            if '/14/' in path:
                return httpx.Response(404)
            filename = 'web.yml' if '/13/' in path else (
                'maven_dev.yml' if '.gitlab-ci-dev.yml' in path else 'maven_root.yml'
            )
            text = (Path('tests/fixtures/ci') / filename).read_text()
            if self.failure and '.job.' in self.failure:
                job = self.failure.split('.job.')[1]
                text = text.replace(job, 'demo_missing_job')
            return httpx.Response(200, text=text)
        services = [service('demo_test', 'demo-modules-order'), service('demo_test', 'demo-web')]
        for entry in services:
            if self.failure == 'service.' + entry['Spec']['Name']:
                entry['Spec']['TaskTemplate']['ContainerSpec']['Image'] = 'demo/demo-wrong:latest'
        data = {
            '/api/endpoints': [] if self.failure == 'portainer.endpoint' else [{'Id': 1}],
            '/api/endpoints/1/docker/info': {'Swarm': {'Cluster': {
                'ID': 'demo-wrong' if self.failure == 'portainer.swarm' else 'abc123def456',
            }}},
            '/api/endpoints/1/docker/services': services,
            '/api/registries': [] if self.failure == 'portainer.registry' else [{'Id': 2}],
        }
        assert path in data, path
        return httpx.Response(200, json=data[path])


def run_check(monkeypatch, configured, upstream):
    monkeypatch.setattr('dce.workspace.doctor.PlatformClient', client_factory(upstream))
    return {item.id: item for item in check(*configured)}


def test_all_checks_pass_and_writes_warn(configured, monkeypatch):
    upstream = Upstream()
    items = run_check(monkeypatch, configured, upstream)
    expected = {
        'config.schema', 'credentials.zentao', 'credentials.gitlab', 'credentials.portainer',
        'zentao.login', 'zentao.product', 'zentao.account', 'gitlab.token', 'gitlab.token_scope',
        'portainer.endpoint', 'portainer.swarm', 'portainer.registry', 'records.file',
        'service.demo_test_demo-modules-order', 'service.demo_test_demo-web',
    }
    for name in ('demo-cloud', 'demo-web', 'demo-pm'):
        expected.update(f'repo.{name}.{suffix}' for suffix in ('path', 'origin'))
    for name, jobs in [('demo-cloud', ['compile_demo_order', 'build_demo_order']),
                       ('demo-web', ['compile_demo_web', 'build_demo_web'])]:
        expected.add(f'repo.{name}.test_branch')
        expected.update(f'repo.{name}.job.{job}' for job in jobs)
    assert set(items) == expected | {'portainer.write', 'zentao.resolve'}
    assert all(items[key].status == 'pass' for key in expected)
    for key, phrase in [('portainer.write', '首次部署'), ('zentao.resolve', '首次使用')]:
        assert items[key].status == 'warn'
        assert phrase in items[key].detail


@pytest.mark.parametrize('failure', [
    'config.schema', 'credentials.zentao', 'credentials.gitlab', 'credentials.portainer',
    'zentao.login', 'zentao.product', 'zentao.account', 'gitlab.token', 'gitlab.token_scope',
    'portainer.endpoint', 'portainer.swarm', 'portainer.registry', 'records.file',
    *[f'repo.{name}.{suffix}' for name in ('demo-cloud', 'demo-web', 'demo-pm')
      for suffix in ('path', 'origin')],
    *[f'repo.{name}.test_branch' for name in ('demo-cloud', 'demo-web')],
    *[f'repo.demo-cloud.job.{job}' for job in ('compile_demo_order', 'build_demo_order')],
    *[f'repo.demo-web.job.{job}' for job in ('compile_demo_web', 'build_demo_web')],
    'service.demo_test_demo-modules-order', 'service.demo_test_demo-web',
])
def test_each_check_has_specific_failure(configured, monkeypatch, failure):
    workspace, settings = configured
    config_path = workspace / '.dce/dce.yaml'
    if failure == 'config.schema':
        config_path.write_text('version: 1')
    elif failure.startswith('credentials.'):
        setattr(settings, failure.split('.')[1], None)
    elif failure == 'zentao.account':
        settings._zentao_account = 'demo-other'
    elif failure.endswith('.path'):
        name = failure.split('.')[1]
        (workspace / name / '.git').rename(workspace / name / '.git-away')
    elif failure.endswith('.origin'):
        git(workspace / failure.split('.')[1], 'remote', 'set-url', 'origin',
            'https://gitlab.example.invalid/demo/demo-other.git')
    elif failure == 'records.file':
        (workspace / 'demo-pm/projects/demo/V1.2.0/缺陷修复记录.md').unlink()
    items = run_check(monkeypatch, configured, Upstream(failure))
    assert items[failure].status == 'fail'
    assert items[failure].detail and items[failure].fix


def test_scope_404_warns_without_failing_token(configured, monkeypatch):
    items = run_check(monkeypatch, configured, Upstream('scope404'))
    assert items['gitlab.token_scope'].status == 'warn'
    assert '404' in items['gitlab.token_scope'].detail
    assert items['gitlab.token'].status == 'pass'


@pytest.mark.parametrize('mismatch', ['missing', 'namespace'])
def test_service_identity_failures(configured, monkeypatch, mismatch):
    upstream = Upstream()

    def handle(request):
        if request.url.path.endswith('/docker/services'):
            entry = service('demo_other', 'demo-modules-order')
            entry['Spec']['Name'] = 'demo_test_demo-modules-order'
            return httpx.Response(200, json=[] if mismatch == 'missing' else [entry])
        return upstream(request)

    items = run_check(monkeypatch, configured, handle)
    assert items['service.demo_test_demo-modules-order'].status == 'fail'


def test_bad_job_reports_repo_file_and_name(configured, monkeypatch):
    items = run_check(monkeypatch, configured, Upstream('repo.demo-cloud.job.compile_demo_order'))
    detail = items['repo.demo-cloud.job.compile_demo_order'].detail
    words = ['demo-cloud', '.gitlab-ci-dev.yml', 'compile_demo_order']
    assert all(word in detail for word in words)


def test_child_trigger_mismatch_fails_configured_jobs(configured, monkeypatch):
    workspace, _ = configured
    config_path = workspace / '.dce/dce.yaml'
    data = yaml.safe_load(config_path.read_text())
    data['repos'][0]['ci']['trigger_job'] = 'demo_missing_trigger'
    config_path.write_text(yaml.safe_dump(data))
    items = run_check(monkeypatch, configured, Upstream())
    item = items['repo.demo-cloud.job.compile_demo_order']
    assert item.status == 'fail' and 'demo_missing_trigger' in item.detail


def test_missing_product_and_records_fields_are_actionable(configured, monkeypatch):
    workspace, _ = configured
    config_path = workspace / '.dce/dce.yaml'
    data = yaml.safe_load(config_path.read_text())
    data['zentao']['product'] = None
    data['records']['file'] = None
    config_path.write_text(yaml.safe_dump(data))
    items = run_check(monkeypatch, configured, Upstream())
    assert items['zentao.product'].status == 'fail'
    assert items['records.file'].status == 'fail'
