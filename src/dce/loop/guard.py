"""Check configured targets before any loop mutation."""

from fnmatch import fnmatchcase
from typing import Any

from dce.errors import DceError, ErrorCode
from dce.workspace.ci_parser import image_path
from dce.workspace.config import PROTECTED, DceConfig, Repo


def require(ok: bool, resource: str, field: str, actual: Any, expected: Any) -> None:
    if not ok:
        raise DceError(ErrorCode.OUT_OF_SCOPE,
                       f'{resource}: {field} 不符，实际 {actual!r}，配置要求 {expected!r}。',
                       '核对 .dce/dce.yaml 和计划中的目标后重新生成计划。')


def check_bug(cfg: DceConfig, bug: dict[str, Any]) -> None:
    product = bug.get('product')
    if isinstance(product, dict):
        product = product.get('id')
    require(cfg.zentao.product is not None and str(product) == str(cfg.zentao.product),
            f"禅道缺陷 {bug.get('id')} HTTP 200", 'product', product, cfg.zentao.product)


def check_branch(cfg: DceConfig, repo: Repo, branch: str | None) -> None:
    resource = f'GitLab 仓库 {repo.name}'
    require(bool(branch) and branch == repo.test_branch, resource,
            'test_branch', branch, repo.test_branch)
    patterns = list(dict.fromkeys([*PROTECTED, *cfg.protected_branches]))
    require(not any(fnmatchcase(branch or '', p) for p in patterns), resource,
            'protected_branches', branch, patterns)


def check_job(cfg: DceConfig, item: dict[str, Any], project_id: int | None,
              job_name: str | None) -> None:
    repo = next((r for r in cfg.repos if r.name == item.get('repo')), None)
    require(repo is not None, 'GitLab job', 'repo', item.get('repo'), [r.name for r in cfg.repos])
    assert repo is not None
    require(repo.gitlab.id is not None and project_id == repo.gitlab.id,
            f'GitLab job {job_name}', 'project_id', project_id, repo.gitlab.id)
    names = [item.get('compile_job'), item.get('build_job')]
    require(bool(job_name) and job_name in names, f'GitLab project {project_id}',
            'job_name', job_name, names)


def check_pipeline_ref(cfg: DceConfig, repo: Repo, ref: str | None) -> None:
    require(bool(ref) and ref == repo.test_branch, f'GitLab project {repo.gitlab.id}',
            'ref', ref, repo.test_branch)
    check_branch(cfg, repo, ref)


def check_service(cfg: DceConfig, service_json: dict[str, Any], swarm_id: str,
                  endpoint: int | None) -> None:
    spec = service_json.get('Spec', {})
    name = spec.get('Name')
    modules = [m for r in cfg.repos for m in r.modules if name in m.services]
    resource = f'Portainer service {name}'
    require(bool(modules), resource, 'service', name,
            [s for r in cfg.repos for m in r.modules for s in m.services])
    require(cfg.portainer.endpoint is not None and endpoint == cfg.portainer.endpoint,
            resource, 'endpoint', endpoint, cfg.portainer.endpoint)
    namespace = spec.get('Labels', {}).get('com.docker.stack.namespace')
    require(namespace == cfg.environment.stack, resource, 'namespace',
            namespace, cfg.environment.stack)
    require(bool(swarm_id) and swarm_id == cfg.environment.swarm_id,
            resource, 'swarm_id', swarm_id, cfg.environment.swarm_id)
    image = image_path(spec.get('TaskTemplate', {}).get('ContainerSpec', {}).get('Image', ''))
    require(all(image == m.image for m in modules), resource, 'image',
            image, [m.image for m in modules])
