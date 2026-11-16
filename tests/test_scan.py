import subprocess
from pathlib import Path

import httpx
import pytest
from test_platforms_read import settings as platform_settings
from test_pom import pom

from dce.workspace.config import load_config
from dce.workspace.scan import scan

CI = Path('tests/fixtures/ci')
settings = platform_settings


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True,
                          text=True, timeout=10).stdout.strip()


def repository(root, name):
    bare = root.parent / f'{root.name}-{name}.git'
    subprocess.run(['git', 'init', '--bare', str(bare)], check=True, capture_output=True)
    subprocess.run(['git', 'clone', str(bare), str(root / name)],
                   check=True, capture_output=True)
    path = root / name
    git(path, 'remote', 'set-url', 'origin', f'http://gitlab.example.invalid/demo/{name}.git')
    return path


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / 'demo-workspace'
    root.mkdir()
    git(root, 'init')
    cloud = repository(root, 'demo-cloud')
    pom(cloud, 'demo-modules/demo-order', 'demo-modules-order', ['demo-common'])
    pom(cloud, 'demo-modules/demo-report', 'demo-modules-report')
    repository(root, 'demo-web')
    pm = repository(root, 'demo-pm')
    records = pm / 'projects/demo/V1.2.0/缺陷修复记录.md'
    records.parent.mkdir(parents=True)
    records.write_text('# demo records')
    return root


@pytest.fixture
def upstream():
    class Upstream:
        missing_project = False
        removed_service = False
        requests = []

        def __call__(self, request):
            self.requests.append(request)
            path = request.url.path
            if path.startswith('/api/v4/projects/demo/'):
                name = path.rsplit('/', 1)[-1]
                if self.missing_project and name == 'demo-cloud':
                    return httpx.Response(404)
                return httpx.Response(200, json={
                    'id': {'demo-cloud': 12, 'demo-web': 13, 'demo-pm': 14}[name],
                    'default_branch': 'main',
                })
            if path.endswith('/repository/branches'):
                names = ['develop', 'develop_v2'] if '/12/' in path else ['develop']
                return httpx.Response(200, json=[{'name': name} for name in names])
            if path.endswith('/raw'):
                if '/14/' in path:
                    return httpx.Response(404)
                name = 'web.yml' if '/13/' in path else (
                    'maven_dev.yml' if '.gitlab-ci-dev.yml' in path else 'maven_root.yml'
                )
                return httpx.Response(200, text=(CI / name).read_text())
            services = [service('demo_test', 'demo-modules-order'),
                        service('demo_test', 'demo-web'), service('demo_other', 'demo-web')]
            if not self.removed_service:
                services.append(service('demo_test', 'demo-modules-report'))
            data = {
                '/api/endpoints': [{'Id': 1, 'Type': 1}],
                '/api/endpoints/1/docker/info': {'Swarm': {'Cluster': {'ID': 'demo123'}}},
                '/api/endpoints/1/docker/services': services,
                '/api/stacks': [{'Id': 31, 'Name': 'demo_test', 'SwarmId': 'demo123'}],
                '/api/registries': [{'Id': 2, 'URL': 'registry.example.invalid:5000'}],
            }
            assert path in data, path
            return httpx.Response(200, json=data[path])

    return Upstream()


def service(namespace, image):
    return {'ID': image, 'Spec': {
        'Name': f'{namespace}_{image}',
        'Labels': {'com.docker.stack.namespace': namespace},
        'TaskTemplate': {'ContainerSpec': {
            'Image': f'registry.example.invalid:5000/demo/{image}:latest@sha256:demo',
        }},
    }}


def test_scan_comments_local_files_and_no_overwrite(workspace, settings, upstream, monkeypatch):
    monkeypatch.setattr('dce.workspace.scan.PlatformClient', client_factory(upstream))
    result = scan(workspace, settings)
    config = load_config(workspace)
    assert config.environment.stack == 'demo_test' and config.portainer.registry_id == 2
    assert config.repos[0].test_branch == 'develop'
    assert config.repos[0].modules[0].services == ['demo_test_demo-modules-order']
    assert config.records.file == 'projects/demo/V1.2.0/缺陷修复记录.md'
    target = workspace / '.dce/dce.yaml'
    before = target.read_text()
    assert any('test_branch: develop' in line and '# TODO(确认):' in line
               for line in before.splitlines())
    assert '.dce/dce.yaml' == result.written and result.proposed is False
    assert (workspace / '.dce/test-notes.md').is_file()
    assert (workspace / '.gitignore').read_text().splitlines() == [
        '.dce/runs/', '.dce/tmp/', '.dce/dce.proposed.yaml',
    ]
    result = scan(workspace, settings)
    assert result.proposed and result.written == '.dce/dce.proposed.yaml'
    assert not result.diff and target.read_text() == before
    upstream.removed_service = True
    result = scan(workspace, settings)
    assert 'demo_test_demo-modules-report' in str(result.diff)
    assert target.read_text() == before
    assert (workspace / '.gitignore').read_text().count('.dce/runs/') == 1


def client_factory(upstream):
    from dce.platforms.http import PlatformClient

    return lambda config, settings: PlatformClient(
        config, settings, transport=httpx.MockTransport(upstream),
    )


def test_missing_project_is_todo_other_repos_continue(workspace, settings, upstream, monkeypatch):
    upstream.missing_project = True
    monkeypatch.setattr('dce.workspace.scan.PlatformClient', client_factory(upstream))
    result = scan(workspace, settings)
    assert any('404' in t['reason'] and 'demo-cloud' in t['reason'] for t in result.todos)
    assert any(r['name'] == 'demo-web' and r['gitlab_id'] == 13 for r in result.repos)


def test_foreign_origin_is_reported_without_gitlab_request(
    workspace, settings, upstream, monkeypatch,
):
    git(workspace / 'demo-cloud', 'remote', 'set-url', 'origin',
        'https://foreign.example.invalid/demo/demo-cloud.git')
    monkeypatch.setattr('dce.workspace.scan.PlatformClient', client_factory(upstream))
    result = scan(workspace, settings)
    assert any('origin' in t['reason'] for t in result.todos)
