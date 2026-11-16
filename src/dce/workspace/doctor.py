from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass
from functools import cache, partial
from pathlib import Path
from typing import Any, Literal

from dce.errors import DceError, ErrorCode
from dce.platforms.gitlab import GitLab
from dce.platforms.http import PlatformClient
from dce.platforms.portainer import Portainer
from dce.redact import redact
from dce.settings import PLATFORMS, Settings
from dce.workspace.ci_parser import CiParseResult, image_path, parse_ci
from dce.workspace.config import Repo, load_config, within
from dce.workspace.scan import _git, _project


@dataclass
class Check:
    id: str
    status: Literal['pass', 'warn', 'fail']
    detail: str | None = None
    fix: str | None = None


def _require(condition: bool, detail: str, fix: str) -> None:
    if not condition:
        raise DceError(ErrorCode.CONFIG_INVALID, detail, fix)


def check(workspace: Path, settings: Settings) -> list[Check]:
    checks: list[Check] = []

    def inspect(identity: str, operation: Callable[[], str | None]) -> None:
        try:
            checks.append(Check(identity, 'pass', operation()))
        except DceError as exc:
            checks.append(Check(identity, 'fail', redact(exc.message, settings.secrets()),
                                exc.hint or '修正此检查项对应的配置，然后重新自检。'))

    fixed = [Check('portainer.write', 'warn', '写权限需首次部署时验证'),
             Check('zentao.resolve', 'warn', '解决权限需首次使用时验证')]
    try:
        config = load_config(workspace)
    except DceError as exc:
        return [Check('config.schema', 'fail', exc.message, exc.hint), *fixed]
    checks.append(Check('config.schema', 'pass'))
    with ExitStack() as stack:
        readers: dict[str, PlatformClient] = {}

        def credential(platform: str) -> str:
            connection = settings.platform(platform)
            readers[platform] = stack.enter_context(PlatformClient(connection, settings))
            return f'{platform}: 连接与进程内凭证已加载'

        for platform in PLATFORMS:
            inspect(f'credentials.{platform}', partial(credential, platform))

        def client(platform: str) -> PlatformClient:
            if platform not in readers:
                raise DceError(
                    ErrorCode.CREDENTIALS_INVALID, f'{platform}: 缺少可用的平台凭证。',
                    f'先修复 credentials.{platform} 检查项。',
                )
            return readers[platform]

        @cache
        def product() -> dict[str, Any]:
            _require(bool(config.zentao.product and config.zentao.product > 0),
                     '禅道 zentao.product: 缺少有效产品 ID。', '填写允许处理的禅道产品 ID。')
            return dict(client('zentao').json(
                f'/api.php/v1/products/{config.zentao.product}/bugs', kind='zentao',
                params={'page': 1, 'limit': 1},
            ))

        def login() -> str:
            client('zentao')
            if settings._zentao_tokens:
                settings._zentao_tokens.lease()
            else:
                try:
                    product()
                except DceError as exc:
                    if exc.code != ErrorCode.NOT_FOUND:
                        raise
            return '禅道 v1 登录凭证可用'

        def account() -> str:
            actual = settings._zentao_account
            _require(bool(actual) and config.zentao.account in {None, actual},
                     '禅道 zentao.account 与凭证中的登录账号不一致或缺少登录账号。',
                     '将 zentao.account 设为凭证对应账号，或省略以使用凭证账号。')
            return '禅道 account 与登录账号一致'

        inspect('zentao.login', login)
        inspect('zentao.product', lambda: (product(), '禅道产品缺陷可读取')[1])
        inspect('zentao.account', account)
        inspect('gitlab.token', lambda: (
            client('gitlab').json('/api/v4/user'), 'GitLab HTTP 200: 令牌可用',
        )[1])

        def token_scope() -> str:
            metadata = GitLab(client('gitlab')).token_self()
            if metadata is None:
                return '404'
            _require('api' in metadata.get('scopes', []),
                     f"GitLab token HTTP 200: 令牌 scopes={metadata.get('scopes', [])}，缺少 api。",
                     '换成带 api scope 的 GitLab 个人访问令牌。')
            return 'GitLab 令牌包含 api scope'

        inspect('gitlab.token_scope', token_scope)
        if checks[-1].detail == '404':
            checks[-1] = Check('gitlab.token_scope', 'warn',
                               'GitLab /personal_access_tokens/self HTTP 404: 无法读取 scopes。',
                               '在 GitLab 令牌设置中确认 api scope。')

        def inspect_repo(repo: Repo) -> None:
            base = f'repo.{repo.name}'
            directory = workspace / repo.path

            def repo_path() -> str:
                _require(directory.is_dir() and (directory / '.git').exists(),
                         f'本地仓库 {repo.name}: {repo.path} 不存在或缺少 .git。',
                         f'在工作区恢复 {repo.path} 仓库。')
                return f'本地仓库 {repo.name} 存在'

            def origin() -> str:
                actual = _project(_git(directory, 'remote', 'get-url', 'origin'),
                                  client('gitlab').config.base_url)
                _require(actual == repo.gitlab.project,
                         f'GitLab 仓库 {repo.name}: 本地 origin 项目 {actual} '
                         f'与配置 {repo.gitlab.project} 不一致。',
                         '核对仓库 origin 与 dce.yaml 中 gitlab.project。')
                return 'origin 与配置一致'

            inspect(f'{base}.path', repo_path)
            inspect(f'{base}.origin', origin)
            if not repo.test_branch and not repo.modules:
                return

            def branch() -> str:
                branches = GitLab(client('gitlab')).branches(
                    repo.gitlab.id or 0, repo.test_branch or '',
                )
                _require(any(b['name'] == repo.test_branch for b in branches),
                         f'GitLab 仓库 {repo.name} 项目 {repo.gitlab.id} HTTP 200: '
                         f'远端分支 {repo.test_branch} 不存在。',
                         '核对 dce.yaml 中该仓库的 test_branch。')
                return f'{repo.test_branch} 远端存在'

            inspect(f'{base}.test_branch', branch)
            parsed: CiParseResult | None = None
            parse_error: DceError | None = None
            try:
                _require(repo.ci is not None, f'GitLab 仓库 {repo.name}: 缺少 ci 配置。',
                         '填写 ci.mode、ci.file 和子流水线的 trigger_job。')
                assert repo.ci is not None
                gitlab = GitLab(client('gitlab'))
                parsed = parse_ci(gitlab.raw_file(str(repo.gitlab.id), repo.ci.file,
                                                  repo.test_branch or ''), repo.test_branch or '')
                if repo.ci.mode == 'child':
                    root = parse_ci(gitlab.raw_file(str(repo.gitlab.id), '.gitlab-ci.yml',
                                                    repo.test_branch or ''), repo.test_branch or '')
                    _require(root.trigger_job == repo.ci.trigger_job
                             and root.trigger_include == repo.ci.file,
                             f'GitLab 仓库 {repo.name}: .gitlab-ci.yml 中 '
                             f'{repo.ci.trigger_job} 未在 {repo.test_branch} 引用 {repo.ci.file}。',
                             '核对子流水线的 trigger_job、file 和测试分支规则。')
            except DceError as exc:
                parse_error = exc
            jobs = {j.name for j in parsed.jobs if j.when_on_branch.get(repo.test_branch or '')
                    not in {None, 'never'}} if parsed else set()
            for module in repo.modules:
                for name in filter(None, [module.compile_job, module.build_job]):
                    def job(job_name: str = name) -> str:
                        if parse_error:
                            raise parse_error
                        _require(job_name in jobs,
                                 f'GitLab 仓库 {repo.name} 项目 {repo.gitlab.id} HTTP 200: '
                                 f'{repo.ci.file if repo.ci else "ci.file"} 中找不到测试分支 '
                                 f'{repo.test_branch} 的 job {job_name}。',
                                 '按测试分支 CI 文件更正该模块的 compile_job/build_job。')
                        return f'{job_name} 在测试分支 CI 中存在'
                    inspect(f'{base}.job.{name}', job)

        for repo in config.repos:
            inspect_repo(repo)

        def endpoint() -> str:
            endpoints = Portainer(client('portainer')).endpoints()
            _require(any(e['Id'] == config.portainer.endpoint for e in endpoints),
                     f'Portainer /api/endpoints HTTP 200: '
                     f'endpoint {config.portainer.endpoint} 不存在。',
                     '选择当前账号可访问的测试 Swarm endpoint。')
            return '测试 endpoint 存在'

        def swarm() -> str:
            actual = Portainer(client('portainer')).swarm_id(config.portainer.endpoint or 0)
            _require(actual == config.environment.swarm_id,
                     f'Portainer endpoint {config.portainer.endpoint} HTTP 200: '
                     f'Swarm.Cluster.ID={actual}，与配置 {config.environment.swarm_id} 不一致。',
                     '核对 environment.swarm_id 与测试 endpoint 所属集群。')
            return 'Swarm 集群 ID 一致'

        inspect('portainer.endpoint', endpoint)
        inspect('portainer.swarm', swarm)

        @cache
        def services() -> list[dict[str, Any]]:
            return Portainer(client('portainer')).services(str(config.portainer.endpoint))

        for repo in config.repos:
            for module in repo.modules:
                for name in module.services:
                    def service(
                        service_name: str = name, expected_image: str | None = module.image,
                    ) -> str:
                        matches = [s for s in services() if s['Spec'].get('Name') == service_name]
                        prefix = (f'Portainer endpoint {config.portainer.endpoint} '
                                  f'服务 {service_name}')
                        _require(len(matches) == 1, f'{prefix} HTTP 200: 服务缺失或名字重复。',
                                 '核对模块 services 与 Portainer 测试服务名。')
                        spec = matches[0]['Spec']
                        namespace = spec.get('Labels', {}).get('com.docker.stack.namespace')
                        _require(namespace == config.environment.stack,
                                 f'{prefix} HTTP 200: namespace={namespace} 与配置 Stack 不一致。',
                                 '核对 environment.stack 和服务 namespace 标签。')
                        container = spec.get('TaskTemplate', {}).get('ContainerSpec', {})
                        image = container.get('Image', '')
                        _require(image_path(image) == expected_image,
                                 f'{prefix} HTTP 200: 镜像路径 {image_path(image)} '
                                 f'与配置 {expected_image} 不一致。',
                                 '按仓库路径精确匹配模块 image。')
                        return '服务存在，namespace 与镜像路径一致'
                    inspect(f'service.{name}', service)

        def registry() -> str:
            registries = Portainer(client('portainer')).registries()
            _require(any(r['Id'] == config.portainer.registry_id for r in registries),
                     f'Portainer /api/registries HTTP 200: registry_id '
                     f'{config.portainer.registry_id} 不存在。', '核对私有镜像 registry_id。')
            return 'registry_id 存在'

        inspect('portainer.registry', registry)

        def record() -> str:
            repo = next((r for r in config.repos if r.name == config.records.repo), None)
            _require(repo is not None and bool(config.records.file),
                     'records.file: 缺少记录仓库或修复记录文件配置。',
                     '填写 records.repo 和 records.file。')
            assert repo is not None and config.records.file is not None
            root = workspace / repo.path
            within(root, config.records.file, 'records.file')
            _require((root / config.records.file).is_file(),
                     f'records.file: 仓库 {repo.name} 中 {config.records.file} 不存在。',
                     '按相对记录仓库根目录的路径填写 records.file。')
            return '缺陷修复记录文件存在'

        inspect('records.file', record)
    return [*checks, *fixed]
