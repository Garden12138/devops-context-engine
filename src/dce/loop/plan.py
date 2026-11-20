"""Map branch changes to configured modules and persist a deployment plan."""

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dce.errors import DceError, ErrorCode
from dce.loop import gitops as git
from dce.loop.bugs import brief
from dce.loop.guard import check_bug
from dce.loop.runs import RECORD_BUG_FIELDS, Run, append_event, load_run, new_run, save_run
from dce.platforms.zentao import ZenTao
from dce.redact import redact
from dce.workspace.config import DceConfig, Module, Repo, validate_config


def make_plan(ws: Path, cfg: DceConfig, bug_ids: list[int], repos: list[str] | None = None,
              feature_branches: dict[str, str] | None = None, run_id: str | None = None,
              add_items: list[dict[str, Any]] | None = None,
              drop_items: list[str] | None = None, *,
              bug_client: Callable[[], ZenTao] | None = None) -> Run:
    validate_config(cfg, ws)
    if not bug_ids or any(b <= 0 for b in bug_ids):
        raise DceError(ErrorCode.CONFIG_INVALID, 'deploy_plan.bug_ids 需要至少一个正数缺陷 ID。')
    configured = {r.name: r for r in cfg.repos}
    features = {r.name: r.feature_branch for r in cfg.repos}
    features.update(feature_branches or {})
    selected = list(dict.fromkeys(repos if repos is not None else
                                 [r.name for r in cfg.repos if r.modules]))
    modules = {f'{r.name}:{m.path}': (r, m) for r in cfg.repos for m in r.modules}
    unknown = (set(selected) | set(feature_branches or {})) - configured.keys()
    if unknown:
        raise DceError(ErrorCode.OUT_OF_SCOPE, f'deploy_plan 仓库未配置：{sorted(unknown)}。',
                       '使用 .dce/dce.yaml repos 中的名字。')
    for addition in add_items or []:
        item_id = f"{addition.get('repo')}:{addition.get('module')}"
        if item_id not in modules or not isinstance(addition.get('reason'), str):
            raise DceError(ErrorCode.OUT_OF_SCOPE,
                           f'add_items {item_id}: 模块未配置或缺少 reason。',
                           '使用配置中的仓库、模块和补充原因。')
    for item_id in drop_items or []:
        if item_id not in modules:
            raise DceError(ErrorCode.OUT_OF_SCOPE, f'drop_items {item_id}: 模块未配置。')
    run = load_run(ws, run_id) if run_id else new_run(ws, bug_ids)
    warnings: list[dict[str, str]] = []
    items: dict[str, dict[str, Any]] = {}
    commits: dict[str, list[dict[str, Any]]] = {}
    unmapped: dict[str, list[str]] = {}

    def warn(code: str, repo: str, reason: str) -> None:
        warnings.append({'code': code, 'message': f'{repo}: {reason}'})

    def add(repo: Repo, module: Module, reason: str, bugs: list[int], required: bool) -> None:
        item_id = f'{repo.name}:{module.path}'
        items[item_id] = {'id': item_id, 'repo': repo.name, 'module': module.path,
                          'kind': module.kind, 'reason': reason, 'bugs': bugs,
                          'required': required, 'compile_job': module.compile_job,
                          'build_job': module.build_job, 'image': module.image,
                          'services': module.services.copy()}

    for name in selected:
        repo = configured[name]
        if not repo.modules:
            continue
        path = ws / repo.path
        feature, test = features[name], repo.test_branch
        if not feature or not test:
            raise DceError(ErrorCode.CONFIG_INVALID,
                           f'仓库 {name}: 缺少 feature_branch 或 test_branch。',
                           '填写 .dce/dce.yaml 分支，或用 feature_branches 指定特性分支。')
        git.run_git(path, 'check-ref-format', '--branch', git.reference(feature))
        has_master = git.run_git(path, 'ls-remote', '--exit-code', '--heads', 'origin',
                                 'refs/heads/master', allowed=(0, 2)).returncode == 0
        git.fetch(path, *dict.fromkeys([feature, test, *(['master'] if has_master else [])]))
        worktree = git.worktree_for_branch(path, feature)
        if worktree and git.status_porcelain(worktree):
            warn('DIRTY', name, f'特性分支 {feature} worktree 有未提交改动；先提交或清理。')
        if git.ahead(path, feature, f'origin/{feature}'):
            warn('UNPUSHED', name, f'{feature} 本地领先 origin；合并前需要普通推送特性分支。')
        if git.worktree_for_branch(path, test) and git.ahead(path, test, f'origin/{test}'):
            warn('COMMITTED_ON_TEST_BRANCH', name,
                 f'{test} 正被检出且本地领先 origin；先把修复提交移到特性分支。')
        entries = git.log_range(path, f'origin/{test}', feature)
        if not entries and not any(a['repo'] == name for a in add_items or []):
            continue
        commits[name] = [{**{k: c[k] for k in ('sha', 'subject')},
                          'bugs': sorted({int(b) for b in re.findall(r'bug#(\d+)', c['subject'])})}
                         for c in entries]
        related = sorted(set(bug_ids) & {b for c in commits[name] for b in c['bugs']})
        base = git.merge_base(path, f'origin/{test}', feature)
        for filename in git.changed_files(path, base, feature):
            matches = [m for m in repo.modules if m.path == '.' or
                       filename == m.path or filename.startswith(m.path.rstrip('/') + '/')]
            if matches:
                module = max(matches, key=lambda m: len(m.path))
                add(repo, module, 'changed', related, True)
            else:
                unmapped.setdefault(name, []).append(filename)
        if name in unmapped:
            warn('UNMAPPED_CHANGES', name, ', '.join(unmapped[name]) +
                 ' 未归属模块；检查后通过 add_items 补充。')
        if has_master:
            merges = git.run_git(path, 'log', '--merges', '--format=%H%x1f%P',
                                  f'origin/master..{feature}', '--').stdout
            for line in merges.splitlines():
                sha, parents = line.split('\x1f')
                second = parents.split()[1]
                if (git.is_ancestor(path, second, f'origin/{test}') and
                        not git.is_ancestor(path, second, 'origin/master')):
                    warn('TEST_BRANCH_MERGED_INTO_FEATURE', name,
                         f'{feature} 的合并提交 {sha} 带入测试分支 {test}；合并前核对提交范围。')
                    break
    for addition in add_items or []:
        repo, module = modules[f"{addition['repo']}:{addition['module']}"]
        add(repo, module, addition['reason'], bug_ids.copy(), True)
    # Dependency expansion also covers downstream repositories outside the change filter.
    pending = list(items)
    for item_id in pending:
        item = items[item_id]
        library = modules[item_id][1]
        if library.kind != 'library':
            continue
        for downstream, (repo, module) in modules.items():
            if library.artifact in module.uses and downstream != item_id:
                if downstream not in items:
                    add(repo, module, f'depends_on:{library.artifact}', item['bugs'].copy(), False)
                    pending.append(downstream)
                else:
                    items[downstream]['bugs'] = sorted(set(
                        items[downstream]['bugs'] + item['bugs']))
    for item_id in drop_items or []:
        items.pop(item_id, None)
    order = order_items(items, modules, cfg.build_order)
    missing = sorted(set(bug_ids) - {b for entries in commits.values() for c in entries
                                    for b in c['bugs']})
    if missing:
        warn('BUGS_WITHOUT_COMMITS', 'deploy_plan',
             f'缺陷 {missing} 没有匹配 bug#ID 的提交；核对提交信息。')
    old_bugs = {b['id']: b for b in run['bugs']}
    run['bugs'] = [old_bugs.get(b, {'id': b}) for b in dict.fromkeys(bug_ids)]
    _populate_bug_metadata(cfg, run, warnings, bug_client)
    run['feature_branches'] = {name: features[name] for name in
                               dict.fromkeys([*commits, *(i['repo'] for i in items.values())])}
    run['plan'] = {'items': [items[i] for i in order], 'order': order, 'commits': commits,
                   'unmapped': unmapped, 'bugs_without_commits': missing, 'warnings': warnings}
    run['stage'] = 'planned'
    append_event(run, 'deploy_plan', 'plan', run['run_id'], 'ok', f'{len(items)} 个模块')
    save_run(ws, run)
    return run


def _populate_bug_metadata(cfg: DceConfig, run: Run, warnings: list[dict[str, str]],
                           bug_client: Callable[[], ZenTao] | None) -> None:
    client = None
    for snapshot in run['bugs']:
        if snapshot.get('title'):
            continue
        bug_id = snapshot['id']
        try:
            if cfg.zentao.product is None:
                raise DceError(ErrorCode.CONFIG_INVALID, '缺少 .dce/dce.yaml 的 zentao.product。')
            if client is None:
                if bug_client is None:
                    raise DceError(ErrorCode.CREDENTIALS_INVALID, '缺少禅道连接或凭证配置。')
                client = bug_client()
            live = client.bug(str(bug_id))
        except DceError as exc:
            reason = redact(exc.message, client.reader.secrets() if client else ())
            warnings.append({'code': 'BUG_METADATA_UNAVAILABLE',
                             'message': f'禅道缺陷 {bug_id} 元数据读取失败：{reason}'})
            snapshot.clear()
            snapshot['id'] = bug_id
            continue
        check_bug(cfg, live)
        fields = brief(live)
        snapshot.update(redact({field: fields[field] for field in (
            *RECORD_BUG_FIELDS, 'opened_by', 'status',
        )}, client.reader.secrets()))


def order_items(items: dict[str, dict[str, Any]], modules: dict[str, tuple[Repo, Module]],
                build_order: list[str]) -> list[str]:
    dependencies = {key: {other for other in items if other != key and
                         modules[other][1].artifact and
                         modules[other][1].artifact in modules[key][1].uses} for key in items}

    def priority(key: str) -> tuple[int, int, str]:
        item = items[key]
        repo = item['repo']
        return (build_order.index(repo) if repo in build_order else len(build_order),
                ['library', 'service', 'web'].index(item['kind']), key)

    ordered: list[str] = []
    while len(ordered) < len(items):
        ready = sorted((key for key, deps in dependencies.items()
                        if key not in ordered and deps.issubset(ordered)), key=priority)
        if not ready:
            raise DceError(ErrorCode.CONFIG_INVALID,
                           f'部署计划 uses 存在依赖环：{sorted(set(items) - set(ordered))}。',
                           '检查 .dce/dce.yaml 模块 artifact/uses，移除循环依赖后重新计划。')
        ordered.extend(ready)
    return ordered
