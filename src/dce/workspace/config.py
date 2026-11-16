import fnmatch
import io
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruamel.yaml import YAML

from dce.errors import DceError, ErrorCode

PROTECTED = ['master', 'main', 'release*', 'prod*', 'uat*']


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Resolve(Model):
    resolution: Literal['fixed'] = 'fixed'
    resolved_build: str = 'trunk'
    assign_to: str = 'opener'


class Zentao(Model):
    product: int | None = None
    account: str | None = None
    resolve: Resolve = Field(default_factory=Resolve)


class Portainer(Model):
    endpoint: int | None = None
    registry_id: int | None = None


class Environment(Model):
    name: Literal['test'] = 'test'
    stack: str
    swarm_id: str
    urls: dict[str, str] = Field(default_factory=dict)
    test_notes: str = '.dce/test-notes.md'


class Records(Model):
    repo: str | None = None
    branch: str | None = None
    file: str | None = None
    assets_dir: str = 'assets'


class Gates(Model):
    fix_plan: Literal['always', 'when_unclear'] = 'when_unclear'
    merge: Literal['always'] = 'always'


class Gitlab(Model):
    project: str
    id: int | None = None


class Ci(Model):
    mode: Literal['direct', 'child']
    file: str
    trigger_job: str | None = None


class Module(Model):
    path: str
    kind: Literal['library', 'service', 'web']
    artifact: str | None = None
    compile_job: str | None = None
    build_job: str | None = None
    image: str | None = None
    services: list[str] = Field(default_factory=list)
    uses: list[str] = Field(default_factory=list)


class Repo(Model):
    name: str
    path: str
    gitlab: Gitlab
    feature_branch: str | None = None
    test_branch: str | None = None
    ci: Ci | None = None
    modules: list[Module] = Field(default_factory=list)


class DceConfig(Model):
    version: Literal[2]
    name: str
    zentao: Zentao
    portainer: Portainer
    environment: Environment
    records: Records
    gates: Gates = Field(default_factory=Gates)
    protected_branches: list[str] = Field(default_factory=lambda: PROTECTED.copy())
    build_order: list[str] = Field(default_factory=list)
    repos: list[Repo]


def invalid(path: str, reason: str) -> None:
    raise DceError(
        ErrorCode.CONFIG_INVALID, f'{path}: {reason}',
        '在工作区 .dce/dce.yaml 中修改对应字段，然后运行 dce setup check。',
    )


def within(root: Path, path: str, field: str) -> None:
    if Path(path).is_absolute() or not (root / path).resolve().is_relative_to(root.resolve()):
        invalid(field, '路径必须在工作区或所属仓库内，检查 .. 和符号链接。')


def validate_config(config: DceConfig, workspace: Path) -> None:
    if not set(PROTECTED).issubset(config.protected_branches):
        invalid('protected_branches', '必须包含默认五项 master/main/release*/prod*/uat*。')
    names: set[str] = set()
    for i, repo in enumerate(config.repos):
        base = f'repos[{i}]'
        if repo.name in names:
            invalid(f'{base}.name', f'仓库名 {repo.name} 重复。')
        names.add(repo.name)
        within(workspace, repo.path, f'{base}.path')
        if repo.test_branch and any(
            fnmatch.fnmatchcase(repo.test_branch, p) for p in config.protected_branches
        ):
            invalid(f'{base}.test_branch', '匹配了 protected_branches。')
        paths: set[str] = set()
        for j, module in enumerate(repo.modules):
            field = f'{base}.modules[{j}]'
            within(workspace / repo.path, module.path, f'{field}.path')
            if module.path in paths:
                invalid(f'{field}.path', '同一仓库内模块路径必须唯一。')
            if module.path == '.' and len(repo.modules) != 1:
                invalid(f'{field}.path', '. 只能单独出现。')
            paths.add(module.path)
            if module.kind == 'library':
                for key in ('artifact', 'compile_job'):
                    if not getattr(module, key):
                        invalid(f'{field}.{key}', 'library 模块必须填写此字段。')
                for key in ('build_job', 'services'):
                    if getattr(module, key):
                        invalid(f'{field}.{key}', 'library 模块必须省略此字段。')
            else:
                if not (module.compile_job or module.build_job):
                    invalid(f'{field}.compile_job', 'compile_job 或 build_job 至少填写一个。')
                for key in ('image', 'services'):
                    if not getattr(module, key):
                        invalid(f'{field}.{key}', 'service/web 模块必须填写此字段。')
            for k, service in enumerate(module.services):
                prefix = config.environment.stack + '_'
                if not service.startswith(prefix):
                    invalid(f'{field}.services[{k}]', f'必须以 {prefix} 开头。')


def load_config(workspace: Path) -> DceConfig:
    path = workspace / '.dce/dce.yaml'
    if not path.is_file():
        raise DceError(
            ErrorCode.CONFIG_MISSING, '.dce/dce.yaml 不存在。', '先运行 dce setup scan。',
        )
    try:
        config = DceConfig.model_validate(yaml.safe_load(path.read_text()))
    except ValidationError as exc:
        error = exc.errors()[0]
        field = ''.join(f'[{k}]' if isinstance(k, int) else f'.{k}' for k in error['loc'])
        invalid(field.lstrip('.'), f"配置不符合类型要求（{error['type']}）。")
        raise AssertionError('unreachable') from None
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        invalid('.dce/dce.yaml', f'{type(exc).__name__}，检查读取权限、编码和 YAML 语法。')
        raise AssertionError('unreachable') from None
    validate_config(config, workspace)
    return config


def dump_config(config: DceConfig) -> str:
    stream = io.StringIO()
    YAML().dump(config.model_dump(exclude_none=True), stream)
    return stream.getvalue()


def locate_workspace(arg: str | None, server_default: Path | None, cwd: Path) -> Path:
    selected = Path(arg) if arg is not None else server_default
    if selected is not None:
        if not selected.is_absolute():
            raise DceError(ErrorCode.WORKSPACE_REQUIRED, 'workspace 必须为绝对路径。')
        selected = selected.resolve()
        if arg is not None and server_default and selected != server_default.resolve():
            raise DceError(
                ErrorCode.WORKSPACE_MISMATCH, '工具 workspace 与启动 --workspace 不一致。',
                '使用启动时绑定的业务工作区，或更正项目级 .cursor/mcp.json 后重载 MCP。',
            )
        return selected
    if (cwd / '.dce/dce.yaml').is_file():
        return cwd.resolve()
    raise DceError(
        ErrorCode.WORKSPACE_REQUIRED,
        '请传入业务工作区绝对路径，或在项目级 .cursor/mcp.json 加 --workspace ${workspaceFolder}。',
    )
