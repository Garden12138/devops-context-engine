import io
import os
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from dce.errors import DceError, ErrorCode
from dce.platforms.gitlab import GitLab
from dce.platforms.http import PlatformClient
from dce.platforms.portainer import Portainer
from dce.settings import Settings
from dce.workspace.ci_parser import image_path, parse_ci
from dce.workspace.config import PROTECTED
from dce.workspace.pom import closure, scan_maven


@dataclass
class ScanResult:
    written: str
    proposed: bool
    repos: list[dict[str, Any]]
    environment: dict[str, Any]
    records_file: str | None
    todos: list[dict[str, str]]
    diff: list[str] | None


def _git(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ['git', '-C', str(repo), *args], shell=False, capture_output=True,
            text=True, timeout=60, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
        )
        if result.returncode:
            raise DceError(
                ErrorCode.GIT_ERROR,
                f'git {repo.name}: 读取 {args[0]} 失败（exit {result.returncode}）。',
                '检查仓库及 origin 配置。',
            )
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DceError(ErrorCode.GIT_ERROR, f'git {repo.name}: {type(exc).__name__}。') from None


def _project(origin: str, base_url: str) -> str:
    if '://' not in origin:
        origin = 'ssh://' + origin.replace(':', '/', 1)
    address = urlsplit(origin)
    if address.hostname != urlsplit(base_url).hostname:
        raise DceError(
            ErrorCode.OUT_OF_SCOPE, 'origin 主机与 GitLab base_url 不一致。',
            '确认本地 origin 属于配置中的 GitLab。',
        )
    return address.path.strip('/').removesuffix('.git')


def _diff(old: Any, new: Any, path: str = '') -> list[str]:
    if old == new:
        return []
    if isinstance(old, dict) and isinstance(new, dict):
        return [entry for key in sorted(old.keys() | new.keys()) for entry in
                _diff(old.get(key), new.get(key), f'{path}.{key}'.lstrip('.'))]
    if isinstance(old, list) and isinstance(new, list):
        identity = 'name' if path == 'repos' else 'path'
        if all(isinstance(item, dict) and identity in item for item in old + new):
            return _diff({i[identity]: i for i in old}, {i[identity]: i for i in new}, path)
    return [f'{path}: {old!r} -> {new!r}']


def scan(workspace: Path, settings: Settings) -> ScanResult:
    yaml = YAML()
    target = workspace / '.dce/dce.yaml'
    previous = yaml.load(target.read_text()) if target.exists() else None
    config = yaml.load('''version: 2
name: demo-platform
zentao: {product: null}
portainer: {endpoint: null, registry_id: null}
environment: {name: test, stack: '', swarm_id: '', urls: {}, test_notes: .dce/test-notes.md}
records: {repo: null, branch: null, file: null, assets_dir: assets}
gates: {fix_plan: when_unclear, merge: always}
protected_branches: []
build_order: []
repos: []
''')
    config['name'] = workspace.name
    config['protected_branches'] = PROTECTED.copy()
    if previous:
        for key in ('name', 'zentao', 'gates', 'protected_branches', 'build_order'):
            config[key] = previous.get(key, config[key])
        config['environment']['urls'] = previous.get('environment', {}).get('urls', {})
    config['zentao'].setdefault('account', settings._zentao_account)
    todos: list[dict[str, str]] = []

    def todo(parent: Any, key: str, path: str, reason: str) -> None:
        reasons = [t['reason'] for t in todos if t['path'] == path] + [reason]
        parent.yaml_add_eol_comment('TODO(确认): ' + '；'.join(reasons), key)
        todos.append({'path': path, 'reason': reason})

    if not config['zentao'].get('product'):
        todo(config['zentao'], 'product', 'zentao.product', '填写允许处理的禅道产品 ID')
    repo_stats: list[dict[str, Any]] = []
    maven: dict[str, Any] = {}
    with PlatformClient(settings.platform('gitlab'), settings) as reader:
        gitlab = GitLab(reader)
        directories = sorted(p for p in workspace.iterdir()
                             if p.is_dir() and not p.is_symlink() and not p.name.startswith('.')
                             and (p / '.git').exists())
        for directory in directories:
            index = len(config['repos'])
            repo = CommentedMap(name=directory.name, path=directory.name)
            config['repos'].append(repo)
            stats: dict[str, Any] = dict(name=directory.name, gitlab_id=None, test_branch=None,
                                         modules=0, services_matched=0, todos=0)
            repo_stats.append(stats)
            before = len(todos)
            try:
                project_path = _project(_git(directory, 'remote', 'get-url', 'origin'),
                                        reader.config.base_url)
                repo['gitlab'] = CommentedMap(project=project_path, id=None)
                project = gitlab.project_by_path(project_path)
                project_id = int(project['id'])
                repo['gitlab']['id'] = stats['gitlab_id'] = project_id
                repo.yaml_add_eol_comment('来自本地 origin 与 GitLab 项目查询', 'gitlab')
                branches = [b['name'] for b in gitlab.branches(project_id, 'develop')
                            if b['name'].startswith('develop')]
                repo['feature_branch'] = _git(directory, 'symbolic-ref', '--short', 'HEAD')
                if branches:
                    branch = sorted(branches)[0]
                    ci_text = gitlab.raw_file(str(project_id), '.gitlab-ci.yml', branch)
                    parsed = parse_ci(ci_text, branch)
                    referenced = sorted(parsed.branches_referenced.intersection(branches))
                    branch = referenced[0] if referenced else branch
                    repo['test_branch'] = stats['test_branch'] = branch
                    if len(branches) > 1 or len(referenced) != 1:
                        todo(repo, 'test_branch', f'repos[{index}].test_branch',
                             f'远端候选 {branches}，CI 引用 {referenced}，请确认测试分支')
                    else:
                        repo.yaml_add_eol_comment('来自 .gitlab-ci.yml 分支规则', 'test_branch')
                    if branch != sorted(branches)[0]:
                        parsed = parse_ci(gitlab.raw_file(str(project_id), '.gitlab-ci.yml',
                                                         branch), branch)
                    ci_file = parsed.trigger_include or '.gitlab-ci.yml'
                    repo['ci'] = CommentedMap(mode='child' if parsed.trigger_include else 'direct',
                                              file=ci_file)
                    if parsed.trigger_job:
                        repo['ci']['trigger_job'] = parsed.trigger_job
                        parsed = parse_ci(gitlab.raw_file(str(project_id), ci_file, branch), branch)
                    repo['modules'] = []
                    maven[directory.name] = scan_maven(directory)
                    uses = closure(maven[directory.name])
                    for module in parsed.modules:
                        path = module.path
                        if path not in maven[directory.name] and path:
                            path = next((p for p, m in maven[directory.name].items()
                                         if path in {m.artifact, m.artifact.split(':')[-1]}), path)
                        if path is None:
                            todo(repo, 'modules', f'repos[{index}].modules',
                                 f'{module.build_job or module.compile_job}: 无法归属模块路径')
                            continue
                        entry = CommentedMap(path=path, kind=module.kind)
                        for key in ('compile_job', 'build_job', 'image'):
                            if (value := getattr(module, key)) is not None:
                                entry[key] = value
                                entry.yaml_add_eol_comment(f'来自 {ci_file}', key)
                        if path in maven[directory.name]:
                            entry['artifact'] = maven[directory.name][path].artifact
                            entry['uses'] = sorted(uses[path])
                        elif module.kind == 'library':
                            entry['artifact'] = None
                            todo(entry, 'artifact', f'repos[{index}].modules.artifact',
                                 f'{path}: 本地 pom 未匹配到 artifact，请确认模块路径')
                        if module.image:
                            entry['services'] = []
                        repo['modules'].append(entry)
                    for warning in parsed.warnings:
                        todo(repo, 'ci', f'repos[{index}].ci', warning)
                    stats['modules'] = len(repo['modules'])
                else:
                    repo['modules'] = []
            except DceError as exc:
                repo.setdefault('gitlab', CommentedMap(project='', id=None))
                todo(repo, 'gitlab', f'repos[{index}].gitlab',
                     f'{directory.name}: {exc.message} {exc.hint or "检查 GitLab 项目与 CI 文件"}')
            stats['todos'] = len(todos) - before
    libraries = {m.get('artifact') for r in config['repos'] for m in r.get('modules', [])
                 if m['kind'] == 'library'}
    for repo in config['repos']:
        local_artifacts = {m.artifact for m in maven.get(repo['name'], {}).values()}
        for module in repo.get('modules', []):
            if 'uses' in module:
                module['uses'] = [a for a in module['uses'] if a in libraries | local_artifacts]
    _discover_environment(config, previous, settings, todo)
    for i, repo in enumerate(config['repos']):
        stats = repo_stats[i]
        stats['services_matched'] = sum(len(m.get('services', [])) for m in repo.get('modules', []))
        stats['todos'] = sum(t['path'].startswith(f'repos[{i}]') for t in todos)
    candidates = [p for r in config['repos'] if not r.get('modules')
                  for p in (workspace / r['path']).rglob('缺陷修复记录.md')
                  if p.resolve().is_relative_to(workspace.resolve())]
    records_file = None
    if candidates:
        record = max(candidates, key=lambda p: p.stat().st_mtime)
        repo = next(r for r in config['repos'] if record.is_relative_to(workspace / r['path']))
        config['records'].update(
            repo=repo['name'],
            branch=_git(workspace / repo['path'], 'symbolic-ref', '--short', 'HEAD'),
            file=record.relative_to(workspace / repo['path']).as_posix(),
        )
        records_file = record.relative_to(workspace).as_posix()
        todo(config['records'], 'file', 'records.file', '来自最近修改的缺陷修复记录.md，请确认版本')
    else:
        todo(config['records'], 'file', 'records.file', '没有找到缺陷修复记录.md，请填写记录位置')
    target.parent.mkdir(exist_ok=True)
    proposed = target.exists()
    written = '.dce/dce.proposed.yaml' if proposed else '.dce/dce.yaml'
    stream = io.StringIO()
    yaml.dump(config, stream)
    try:
        with (workspace / written).open('w' if proposed else 'x') as output:
            output.write(stream.getvalue())
    except FileExistsError:
        proposed = True
        previous = yaml.load(target.read_text())
        written = '.dce/dce.proposed.yaml'
        (workspace / written).write_text(stream.getvalue())
    notes = target.parent / 'test-notes.md'
    if not notes.exists():
        notes.write_text('# 浏览器测试知识\n\n入口：\n\niframe：\n\n账号要求：\n\n参照系统：\n')
    if (workspace / '.git').exists():
        ignore = workspace / '.gitignore'
        text = ignore.read_text() if ignore.exists() else ''
        missing = [p for p in ('.dce/runs/', '.dce/tmp/', '.dce/dce.proposed.yaml')
                   if p not in text.splitlines()]
        if missing:
            ignore.write_text(text + ('\n' if text and not text.endswith('\n') else '')
                              + '\n'.join(missing) + '\n')
    environment = {key: config['environment'][key] for key in ('stack', 'swarm_id')}
    environment.update(config['portainer'])
    return ScanResult(written, proposed, repo_stats, environment, records_file,
                      todos, _diff(previous, config) if proposed else None)


def _discover_environment(config: Any, previous: Any, settings: Settings, todo: Any) -> None:
    environment = config['environment']
    with PlatformClient(settings.platform('portainer'), settings) as reader:
        portainer = Portainer(reader)
        selected = (previous or {}).get('portainer', {}).get('endpoint')
        candidates: dict[int, str] = {}
        for endpoint in portainer.endpoints():
            try:
                candidates[int(endpoint['Id'])] = portainer.swarm_id(int(endpoint['Id']))
            except DceError:
                continue
        if selected not in candidates:
            selected = next(iter(candidates)) if len(candidates) == 1 else None
        config['portainer']['endpoint'] = selected
        if selected is None:
            todo(config['portainer'], 'endpoint', 'portainer.endpoint',
                 f'Swarm endpoint 候选 {list(candidates)}，请手动选择')
            return
        environment['swarm_id'] = candidates[selected]
        config['portainer'].yaml_add_eol_comment('来自 Portainer Swarm endpoint', 'endpoint')
        environment.yaml_add_eol_comment('来自 Docker Swarm.Cluster.ID', 'swarm_id')
        services = portainer.services(str(selected))
        images = {m['image'] for r in config['repos'] for m in r.get('modules', [])
                  if m.get('image')}
        counts: Counter[str] = Counter()
        for service in services:
            spec = service['Spec']
            image = spec.get('TaskTemplate', {}).get('ContainerSpec', {}).get('Image', '')
            namespace = spec.get('Labels', {}).get('com.docker.stack.namespace')
            if image_path(image) in images and namespace:
                counts[namespace] += 1
        stack = counts.most_common(1)[0][0] if counts else ''
        environment['stack'] = stack
        environment.yaml_add_eol_comment('来自镜像路径精确匹配最多的 namespace', 'stack')
        tied = [s for s, count in counts.items() if count == counts.get(stack)]
        if len(tied) != 1:
            todo(environment, 'stack', 'environment.stack',
                 f'镜像匹配 namespace 候选 {tied}，请确认')
        stacks = [s for s in portainer.stacks() if s.get('Name') == stack]
        if not stacks or any(s.get('SwarmId') != environment['swarm_id'] for s in stacks):
            todo(environment, 'stack', 'environment.stack',
                 '这个 Stack 缺失或属于另一个集群，请核对')
        registry_hosts: set[str] = set()
        for i, repo in enumerate(config['repos']):
            for j, module in enumerate(repo.get('modules', [])):
                if not module.get('image'):
                    continue
                matches = []
                for service in services:
                    spec = service['Spec']
                    image = spec.get('TaskTemplate', {}).get('ContainerSpec', {}).get('Image', '')
                    if (spec.get('Labels', {}).get('com.docker.stack.namespace') == stack
                            and image_path(image) == module['image']):
                        matches.append(spec['Name'])
                        registry_hosts.add(image.split('/')[0])
                module['services'] = sorted(matches)
                module.yaml_add_eol_comment('来自同 Stack 的镜像仓库路径精确匹配', 'services')
                if not matches:
                    todo(module, 'services', f'repos[{i}].modules[{j}].services',
                         f"Portainer {stack}: 无镜像路径 {module['image']} 对应服务")
        registries = [r for r in portainer.registries()
                      if re.sub(r'^https?://', '', r.get('URL', '')).rstrip('/') in registry_hosts]
        if len(registries) == 1:
            config['portainer']['registry_id'] = registries[0]['Id']
            config['portainer'].yaml_add_eol_comment('来自镜像 registry 主机匹配', 'registry_id')
        else:
            todo(config['portainer'], 'registry_id', 'portainer.registry_id',
                 f'镜像 registry 匹配到 {len(registries)} 个注册表，请确认 registry_id')
