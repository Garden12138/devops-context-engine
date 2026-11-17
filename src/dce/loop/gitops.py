"""Bounded git subprocesses and read operations used by deployment planning."""

import os
import subprocess
from pathlib import Path
from typing import Any

from dce.errors import DceError, ErrorCode
from dce.redact import redact


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
