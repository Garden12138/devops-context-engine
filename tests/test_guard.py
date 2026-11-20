from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from dce.errors import DceError, ErrorCode
from dce.loop.guard import (
    check_branch,
    check_bug,
    check_job,
    check_pipeline_ref,
    check_service,
)
from dce.workspace.config import DceConfig


@pytest.fixture
def cfg():
    return DceConfig.model_validate(yaml.safe_load(Path('examples/dce.example.yaml').read_text()))


def denied(call, field):
    with pytest.raises(DceError) as exc:
        call()
    assert exc.value.code == ErrorCode.OUT_OF_SCOPE
    assert field in exc.value.message and exc.value.hint


def test_bug_product(cfg):
    check_bug(cfg, {'id': 4336, 'product': cfg.zentao.product})
    denied(lambda: check_bug(cfg, {'id': 4336, 'product': 999}), 'product')
    denied(lambda: check_bug(cfg, {'id': 4336}), 'product')


def test_branch_matches_config(cfg):
    repo = cfg.repos[1]
    check_branch(cfg, repo, repo.test_branch)
    denied(lambda: check_branch(cfg, repo, 'develop-other'), 'test_branch')


@pytest.mark.parametrize('branch', ['master', 'main', 'release', 'release/v2', 'production',
                                    'prod', 'uat', 'uat-next', 'demo-protected'])
def test_branch_is_protected_even_with_tampered_config(cfg, branch):
    cfg.protected_branches = ['demo-protected']  # built-in protection remains mandatory
    repo = cfg.repos[1].model_copy(update={'test_branch': branch})
    denied(lambda: check_branch(cfg, repo, branch), 'protected_branches')


def test_missing_branch(cfg):
    repo = cfg.repos[1].model_copy(update={'test_branch': None})
    denied(lambda: check_branch(cfg, repo, None), 'test_branch')


def test_job_name_and_project(cfg):
    repo = cfg.repos[1]
    module = repo.modules[0]
    item = {'repo': repo.name, 'compile_job': module.compile_job, 'build_job': module.build_job}
    for name in (module.compile_job, module.build_job):
        check_job(cfg, item, repo.gitlab.id, name)
    denied(lambda: check_job(cfg, item, 999, module.compile_job), 'project_id')
    denied(lambda: check_job(cfg, item, repo.gitlab.id, 'compile_demo_other'), 'job_name')
    denied(lambda: check_job(cfg, {**item, 'repo': 'demo-unknown'}, 12, 'x'), 'repo')
    denied(lambda: check_job(cfg, item, repo.gitlab.id, None), 'job_name')


def test_pipeline_ref(cfg):
    repo = cfg.repos[1]
    check_pipeline_ref(cfg, repo, repo.test_branch)
    denied(lambda: check_pipeline_ref(cfg, repo, 'feature/1.2.0'), 'ref')
    repo.test_branch = 'main'
    denied(lambda: check_pipeline_ref(cfg, repo, 'main'), 'protected_branches')


def service(cfg):
    module = cfg.repos[1].modules[0]
    return {'ID': 'demo1', 'Spec': {'Name': module.services[0],
            'Labels': {'com.docker.stack.namespace': cfg.environment.stack},
            'TaskTemplate': {'ContainerSpec': {
                'Image': f'registry.example.invalid:5000/{module.image}:dev@sha256:abc'}}}}


def test_service_all_checks_pass(cfg):
    check_service(cfg, service(cfg), cfg.environment.swarm_id, cfg.portainer.endpoint)
    unqualified = service(cfg)
    unqualified['Spec']['TaskTemplate']['ContainerSpec']['Image'] = cfg.repos[1].modules[0].image
    check_service(cfg, unqualified, cfg.environment.swarm_id, cfg.portainer.endpoint)


@pytest.mark.parametrize('field', ['service', 'namespace', 'swarm_id', 'image', 'endpoint'])
def test_service_each_check_fails_independently(cfg, field):
    value = deepcopy(service(cfg))
    swarm, endpoint = cfg.environment.swarm_id, cfg.portainer.endpoint
    if field == 'service':
        value['Spec']['Name'] = 'demo_test_demo-unknown'
    elif field == 'namespace':
        value['Spec']['Labels']['com.docker.stack.namespace'] = 'demo_other'
    elif field == 'swarm_id':
        swarm = 'demo-other'
    elif field == 'image':
        value['Spec']['TaskTemplate']['ContainerSpec']['Image'] = 'demo/demo-order-extra:dev'
    else:
        endpoint = 999
    denied(lambda: check_service(cfg, value, swarm, endpoint), field)
