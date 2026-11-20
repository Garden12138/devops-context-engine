"""Bounded git subprocesses and read operations used by deployment planning."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from dce.errors import DceError, ErrorCode
from dce.loop.guard import check_branch
from dce.loop.runs import Run, append_event, now, save_run
from dce.redact import redact
from dce.workspace.config import DceConfig, Repo


def run_git(repo: Path, *args: str, allowed: tuple[int, ...] = (0,)
            ) -> subprocess.CompletedProcess[str]:
    command = ['git', *args]
    try:
        result = subprocess.run(command, cwd=repo, shell=False, timeout=60,
                                env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'},
                                text=True, capture_output=True)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DceError(ErrorCode.GIT_ERROR,
                       f'Git {repo.name} {args[0]}: {type(exc).__name__}: {redact(str(exc))}',
                       '检查 git 安装、仓库路径和 origin 可达性；命令超时为 60 秒。') from None
    if result.returncode not in allowed:
        tail = '\n'.join(result.stderr.splitlines()[-20:])
        raise DceError(ErrorCode.GIT_ERROR,
                       f'Git {repo.name} {" ".join(args)} 退出码 {result.returncode}: '
                       f'{redact(tail)}', '按 stderr 修正仓库、分支或 origin 访问权限后重试。')
    return result


def reference(ref: str) -> str:
    if not ref or ref.startswith('-') or any(c in ref for c in ('\x00', '\n', '\r')):
        raise DceError(ErrorCode.GIT_ERROR, f'Git 引用 {ref!r}: 空值或含非法选项字符。',
                       '使用配置中的有效分支名或提交 SHA。')
    return ref


def fetch(repo: Path, *branches: str) -> None:
    run_git(repo, 'fetch', 'origin', *(reference(b) for b in branches))


def log_range(repo: Path, a: str, b: str) -> list[dict[str, Any]]:
    output = run_git(repo, 'log', '--format=%H%x1f%s%x1f%an%x1f%aI',
                     f'{reference(a)}..{reference(b)}', '--').stdout
    return [dict(zip(('sha', 'subject', 'author', 'date'), line.split('\x1f', 3), strict=True))
            for line in output.splitlines() if line]


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    output = run_git(repo, 'diff', '--name-only', '-z', reference(base), reference(head), '--')
    return [name for name in output.stdout.split('\x00') if name]


def merge_base(repo: Path, a: str, b: str) -> str:
    return run_git(repo, 'merge-base', reference(a), reference(b)).stdout.strip()


def worktree_for_branch(repo: Path, branch: str) -> Path | None:
    output = run_git(repo, 'worktree', 'list', '--porcelain', '-z').stdout
    path: Path | None = None
    for field in output.split('\x00'):
        if field.startswith('worktree '):
            path = Path(field.removeprefix('worktree ')).resolve()
        elif field == f'branch refs/heads/{branch}':
            return path
    return None


def status_porcelain(path: Path) -> str:
    return run_git(path, 'status', '--porcelain').stdout.strip()


def ahead(repo: Path, local: str, remote: str) -> int:
    return int(run_git(repo, 'rev-list', '--count',
                       f'{reference(remote)}..{reference(local)}', '--').stdout)


def is_ancestor(repo: Path, a: str, b: str) -> bool:
    return run_git(repo, 'merge-base', '--is-ancestor', reference(a), reference(b),
                   allowed=(0, 1)).returncode == 0


MergeResult = dict[str, Any]


class _MergeConflict(DceError):
    def __init__(self, message: str, files: list[str]) -> None:
        super().__init__(ErrorCode.GIT_CONFLICT, message,
                         '在特性分支解决冲突并自审，重新生成计划并取得合并确认。')
        self.files = files


def _push(path: Path, refspec: str, run: Run, ws: Path, target: str) -> None:
    result = run_git(path, 'push', 'origin', refspec, allowed=(0, 1, 128))
    error = None
    if result.returncode:
        error = DceError(ErrorCode.GIT_PUSH_REJECTED,
                         f'Git {target} push 退出码 {result.returncode}: '
                         f'{redact(result.stderr.strip())}',
                         '先 pull/rebase 特性分支；测试分支竞争时重新生成计划后重试。')
    append_event(run, 'merge_to_test', 'push', target, 'error' if error else 'ok',
                 error.message if error else refspec,
                 error_code=error.code.value if error else None)
    save_run(ws, run)
    if error:
        raise error


def _merge_attempt(ws: Path, cfg: DceConfig, path: Path, repo: Repo, feature: str, run: Run
                   ) -> str:
    directory = ws / '.dce/tmp'
    if ((ws / '.dce').is_symlink() or directory.is_symlink()
            or not directory.resolve().is_relative_to(ws.resolve())):
        raise DceError(ErrorCode.OUT_OF_SCOPE, f'Git {repo.name}: .dce/tmp 路径越出工作区。',
                       '将 .dce/tmp 改为工作区内的普通目录。')
    directory.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='merge-', dir=directory)).resolve()
    temporary.rmdir()
    added = False
    try:
        run_git(path, 'worktree', 'add', '--detach', str(temporary), f'origin/{repo.test_branch}')
        added = True
        bugs = ' '.join(f"bug#{b['id']}" for b in run['bugs'])
        message = f"Merge branch '{feature}' into {repo.test_branch} ({bugs})"
        result = run_git(temporary, 'merge', '--no-ff', '--no-edit', '-m', message,
                         f'origin/{feature}', allowed=(0, 1))
        if result.returncode:
            files = run_git(temporary, 'diff', '--name-only', '--diff-filter=U', '-z').stdout
            run_git(temporary, 'merge', '--abort')
            raise _MergeConflict(
                f'Git {repo.name} merge 退出码 {result.returncode}: '
                f'{feature} → {repo.test_branch} 冲突文件：'
                + ', '.join(files.strip('\x00').split('\x00')),
                [f for f in files.split('\x00') if f],
            )
        sha = run_git(temporary, 'rev-parse', 'HEAD').stdout.strip()
        check_branch(cfg, repo, repo.test_branch)
        _push(temporary, f'HEAD:refs/heads/{repo.test_branch}', run, ws,
              f'{repo.name}→{repo.test_branch}')
        return sha
    finally:
        if added:
            run_git(path, 'worktree', 'remove', str(temporary))


def merge_repo(ws: Path, cfg: DceConfig, run: Run, repo: Repo,
               approved_by_user: bool) -> MergeResult:
    check_branch(cfg, repo, repo.test_branch)
    feature = run.get('feature_branches', {}).get(repo.name) or repo.feature_branch
    result: MergeResult = {'repo': repo.name, 'feature': feature, 'test_branch': repo.test_branch}
    target = f'{repo.name}→{repo.test_branch}'
    try:
        if cfg.gates.merge == 'always' and approved_by_user is not True:
            raise DceError(ErrorCode.PRECONDITION_FAILED,
                           f'Git {repo.name}: gates.merge=always 要求 approved_by_user=true。',
                           '展示 diff 摘要、自审结论和部署计划，取得用户同意并确认宿主工具弹窗。')
        if not any(i['repo'] == repo.name for i in run.get('plan', {}).get('items', [])):
            raise DceError(ErrorCode.PRECONDITION_FAILED,
                           f'Git {repo.name}: run {run["run_id"]} 的计划没有该仓库条目。',
                           '先调用 deploy_plan 将该仓库纳入计划。')
        path = (ws / repo.path).resolve()
        if not path.is_relative_to(ws.resolve()):
            raise DceError(ErrorCode.OUT_OF_SCOPE, f'Git {repo.name}: path 越出工作区。',
                           '更正配置 repos[].path。')
        if feature is None:
            raise DceError(ErrorCode.PRECONDITION_FAILED, f'Git {repo.name}: feature_branch 缺失。',
                           '在配置或部署计划中填写特性分支。')
        reference(feature)
        worktree = worktree_for_branch(path, feature)
        if worktree and status_porcelain(worktree):
            raise DceError(ErrorCode.GIT_DIRTY,
                           f'Git {repo.name}: 特性分支 worktree 有未提交改动。',
                           '提交或暂存特性分支改动后重新生成计划。')
        current = run_git(path, 'symbolic-ref', '--quiet', '--short', 'HEAD', allowed=(0, 1))
        if current.stdout.strip() == repo.test_branch and ahead(
            path, str(repo.test_branch), f'origin/{repo.test_branch}',
        ):
            raise DceError(ErrorCode.PRECONDITION_FAILED,
                           f'Git {repo.name}: 当前检出测试分支 {repo.test_branch}'
                           ' 且本地领先 origin。',
                           '先将本地测试分支上的修复整理到特性分支，再生成计划。')
        _push(path, f'{feature}:refs/heads/{feature}', run, ws, f'{repo.name}:{feature}')
        fetch(path, feature, str(repo.test_branch))
        feature_sha = run_git(path, 'rev-parse', f'origin/{feature}').stdout.strip()
        result['status'] = 'merged'
        for attempt in range(2):
            check_branch(cfg, repo, repo.test_branch)
            if is_ancestor(path, f'origin/{feature}', f'origin/{repo.test_branch}'):
                sha = run_git(path, 'rev-parse', f'origin/{repo.test_branch}').stdout.strip()
                result['status'] = 'already_merged'
                break
            try:
                sha = _merge_attempt(ws, cfg, path, repo, feature, run)
                break
            except DceError as exc:
                if exc.code != ErrorCode.GIT_PUSH_REJECTED or attempt == 1:
                    raise
                fetch(path, str(repo.test_branch))
        result.update(feature_sha=feature_sha, merge_sha=sha, merged_at=now())
        run['merges'][repo.name] = {k: result[k] for k in (
            'feature_sha', 'merge_sha', 'merged_at', 'test_branch')}
        run['stage'] = 'merged'
        append_event(run, 'merge_to_test', 'merge', target, 'ok',
                     f'approved_by_user={approved_by_user}; merge_sha={sha}')
    except DceError as exc:
        result.update(status=('conflict' if exc.code == ErrorCode.GIT_CONFLICT else
                              'push_rejected' if exc.code == ErrorCode.GIT_PUSH_REJECTED else
                              'rejected'), error=exc.as_dict())
        if isinstance(exc, _MergeConflict):
            result['files'] = exc.files
            run['stage'] = 'fixing'
        append_event(run, 'merge_to_test', 'merge', target, 'error', exc.message,
                     error_code=exc.code.value)
    save_run(ws, run)
    return result


def merge_repositories(ws: Path, cfg: DceConfig, run: Run, repos: list[str] | None = None,
                       approved_by_user: bool = False) -> dict[str, Any]:
    names = list(dict.fromkeys(repos if repos is not None else
                              [i['repo'] for i in run.get('plan', {}).get('items', [])]))
    if not names:
        raise DceError(ErrorCode.PRECONDITION_FAILED,
                       f'GitLab run {run["run_id"]}: 计划没有可合并的仓库。',
                       '先调用 deploy_plan 生成包含仓库条目的计划。')
    results = []
    configured = {r.name: r for r in cfg.repos}
    for name in names:
        try:
            if name not in configured:
                raise DceError(ErrorCode.OUT_OF_SCOPE, f'GitLab repo {name}: 不在配置中。',
                               '使用配置和部署计划中的仓库名。')
            results.append(merge_repo(ws, cfg, run, configured[name], approved_by_user))
        except DceError as exc:
            results.append({'repo': name, 'status': 'rejected', 'error': exc.as_dict()})
            append_event(run, 'merge_to_test', 'merge', name, 'error', exc.message,
                         error_code=exc.code.value)
            save_run(ws, run)
    blocked = [r['repo'] for r in results if r['status'] not in {'merged', 'already_merged'}]
    return {'ok': True, 'summary': '；'.join(f"{r['repo']}: {r['status']}" for r in results),
            'data': {'results': results},
            'next': f'先处理这些仓库：{", ".join(blocked)}。' if blocked else '调用 ci_build。'}
