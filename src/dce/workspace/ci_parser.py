import re
import shlex
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import yaml

from dce.errors import DceError, ErrorCode

VARIABLE = re.compile(r'\$(?:\{([A-Za-z_]\w*)\}|([A-Za-z_]\w*))')
BRANCH = re.compile(
    r'''^\$CI_COMMIT_(?:REF_NAME|BRANCH)\s*(?:==\s*(["'])([^"']+)\1|=~\s*/\^([^/]+)\$/)$'''
)


@dataclass
class CiJob:
    name: str
    stage: str | None
    when_on_branch: dict[str, str]
    needs: list[str]
    changes: list[str]
    variables: dict[str, str]
    script: list[str]
    trigger_include: str | None
    image_pushes: list[str]
    maven_projects: list[str]
    maven_deploy: bool


@dataclass
class ModuleGuess:
    path: str | None
    kind: str
    compile_job: str | None
    build_job: str | None
    image: str | None


@dataclass
class CiParseResult:
    jobs: list[CiJob] = field(default_factory=list)
    trigger_include: str | None = None
    trigger_job: str | None = None
    branches_referenced: set[str] = field(default_factory=set)
    modules: list[ModuleGuess] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def expand(value: str, variables: dict[str, str]) -> str:
    for _ in range(10):
        updated = VARIABLE.sub(
            lambda m: variables.get(m[1] or m[2], m[0]), value,
        )
        if updated == value:
            break
        value = updated
    return value


def image_path(value: str) -> str:
    value = re.sub(r'^\$(?:\w+|\{\w+\})/', '', value).split('@', 1)[0]
    parts = value.split('/')
    if len(parts) > 1 and ('.' in parts[0] or ':' in parts[0] or parts[0] == 'localhost'):
        parts.pop(0)
    parts[-1] = parts[-1].split(':', 1)[0]
    return '/'.join(parts)


def _merge(base: dict[str, Any], child: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    if depth > 20:
        raise ValueError('嵌套字典超过 20 层，检查 YAML 别名循环')
    result = deepcopy(base)
    for key, value in child.items():
        result[key] = (
            _merge(result[key], value, depth + 1)
            if isinstance(value, dict) and isinstance(result.get(key), dict) else deepcopy(value)
        )
    return result


def _rules(job: dict[str, Any], branch: str, result: CiParseResult) -> tuple[dict[str, str], bool]:
    rules = job.get('rules', [])
    mapping: dict[str, str] = {}
    active = not rules
    selected = False
    for rule in rules:
        expression = rule.get('if')
        if expression is None:
            if rule.get('when') != 'never' and not selected:
                mapping[branch] = rule.get('when', 'on_success')
                active = True
                selected = True
            continue
        match = BRANCH.fullmatch(str(expression).strip())
        if match is None:
            result.warnings.append(f"未知 rules 表达式: {expression}")
            continue
        name = match[2] or match[3]
        result.branches_referenced.add(name)
        mapping.setdefault(name, rule.get('when', 'on_success'))
        if name == branch and not selected:
            active = rule.get('when') != 'never'
            selected = True
    if not rules:
        mapping[branch] = job.get('when', 'on_success')
        active = mapping[branch] != 'never'
    return mapping, active


def _job(name: str, data: dict[str, Any], branch: str, result: CiParseResult) -> tuple[CiJob, bool]:
    variables = {str(k): str(v) for k, v in data.get('variables', {}).items()}
    variables.update(CI_COMMIT_BRANCH=branch, CI_COMMIT_REF_NAME=branch)
    variables = {k: expand(v, variables) for k, v in variables.items()}
    when, active = _rules(data, branch, result)
    changes: list[str] = []
    for rule in data.get('rules', []):
        patterns = rule.get('changes', [])
        if isinstance(patterns, dict):
            patterns = patterns.get('paths', [])
        changes.extend(expand(str(p), variables) for p in patterns)
    script = data.get('script', [])
    script = [script] if isinstance(script, str) else script
    pushes: list[str] = []
    builds: list[str] = []
    projects: list[str] = []
    deploy = False
    for line in script:
        for command in re.split(r'[;\n]', str(line)):
            tokens = shlex.split(command)
            if tokens[:1] == ['export']:
                for assignment in tokens[1:]:
                    if '=' in assignment:
                        key, value = assignment.split('=', 1)
                        variables[key] = expand(value, variables)
                continue
            tokens = [expand(t, variables) for t in tokens]
            if tokens[:2] == ['docker', 'push'] and len(tokens) > 2:
                pushes.append(tokens[2])
            elif tokens[:2] == ['docker', 'build']:
                for index, token in enumerate(tokens[:-1]):
                    if token in {'-t', '--tag'}:
                        builds.append(tokens[index + 1])
            if tokens[:1] in (['mvn'], ['./mvnw']):
                deploy |= 'deploy' in tokens
                for index, token in enumerate(tokens[:-1]):
                    if token in {'-pl', '--projects'}:
                        projects.extend(tokens[index + 1].split(','))
    include = data.get('trigger', {})
    include = include.get('include') if isinstance(include, dict) else None
    if isinstance(include, list):
        include = next(
            (i.get('local') for i in include if isinstance(i, dict) and 'local' in i), None,
        )
    if isinstance(include, dict):
        include = include.get('local')
    return CiJob(
        name, data.get('stage'), when,
        [n['job'] if isinstance(n, dict) else str(n) for n in data.get('needs', [])],
        changes, variables, script, include if isinstance(include, str) else None,
        pushes or builds, projects, deploy,
    ), active


def _module_path(job: CiJob) -> str | None:
    for pattern in job.changes:
        path = re.split(r'[?*\[]', pattern, maxsplit=1)[0].rstrip('/')
        if path and not VARIABLE.search(path):
            return path
    return job.maven_projects[0] if job.maven_projects else None


def parse_ci(text: str, branch: str) -> CiParseResult:
    try:
        if len(text.encode('utf-8')) > 1024 * 1024:
            raise ValueError('单个 CI 文件超过 1MB')
        for count, _ in enumerate(yaml.scan(text), 1):
            if count > 50000:
                raise ValueError('CI YAML token 数超过 50000')
        source = yaml.safe_load(text)
        if not isinstance(source, dict):
            raise ValueError('CI 顶层必须是映射')
        result = CiParseResult()

        def resolve(name: str, chain: tuple[str, ...] = ()) -> dict[str, Any]:
            if name in chain or len(chain) > 5:
                raise ValueError(f'{name}: extends 循环或超过 5 层')
            data = source.get(name)
            if not isinstance(data, dict):
                raise ValueError(f'{name}: extends 模板不存在或格式无效')
            parents = data.get('extends', [])
            parents = [parents] if isinstance(parents, str) else parents
            merged: dict[str, Any] = {}
            for parent in parents:
                merged = _merge(merged, resolve(parent, (*chain, name)))
            return _merge(merged, {k: v for k, v in data.items() if k != 'extends'})

        active_jobs: dict[str, CiJob] = {}
        reserved = {'variables', 'stages', 'default', 'workflow', 'include', 'image', 'services',
                    'before_script', 'after_script', 'cache'}
        for name, data in source.items():
            if str(name).startswith('.') or name in reserved or not isinstance(data, dict):
                continue
            merged = _merge({'variables': source.get('variables', {})}, resolve(name))
            job, active = _job(name, merged, branch, result)
            result.jobs.append(job)
            if active:
                active_jobs[name] = job
                if job.trigger_include:
                    result.trigger_include, result.trigger_job = job.trigger_include, name
        for job in active_jobs.values():
            if job.image_pushes:
                dependencies = [active_jobs[n] for n in job.needs if n in active_jobs]
                compile_job = next((j for j in dependencies if not j.image_pushes), None)
                path = _module_path(compile_job or job)
                kind = 'service' if path else 'web'
                if path is None and compile_job:
                    path = '.'
                if path is None:
                    result.warnings.append(f'{job.name}: 无 needs compile 配对，模块路径待确认')
                if len(job.image_pushes) > 1:
                    result.warnings.append(f'{job.name}: 多个镜像目标，分别确认模块路径')
                for image in dict.fromkeys(job.image_pushes):
                    result.modules.append(ModuleGuess(
                        path, kind, compile_job.name if compile_job else None,
                        job.name, image_path(image),
                    ))
            elif job.maven_deploy:
                library_paths: list[str | None] = list(job.maven_projects) or [None]
                for path in library_paths:
                    result.modules.append(ModuleGuess(path, 'library', job.name, None, None))
        return result
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, yaml.YAMLError) as exc:
        reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        raise DceError(
            ErrorCode.CONFIG_INVALID, f'GitLab CI: {reason}',
            '检查 CI YAML、extends 链及变量定义。',
        ) from None
