import subprocess

import pytest
from gitfixture import GitFixture

from dce.errors import DceError, ErrorCode
from dce.loop.gitops import (
    ahead,
    changed_files,
    fetch,
    is_ancestor,
    log_range,
    merge_base,
    run_git,
    status_porcelain,
    worktree_for_branch,
)


@pytest.fixture
def git_repo(tmp_path):
    return GitFixture(tmp_path / 'demo-git')


def test_read_operations_and_fetch(git_repo):
    fixture, repo = git_repo, git_repo.work
    base = fixture.git(repo, 'rev-parse', 'develop')
    sha = fixture.commit('demo-module/a b.txt', 'demo feature', 'fix: demo bug#4336')
    assert ahead(repo, 'feature/1.2.0', 'origin/feature/1.2.0') == 1
    assert is_ancestor(repo, base, sha)
    assert not is_ancestor(repo, sha, base)
    assert merge_base(repo, 'develop', 'feature/1.2.0') == base
    commits = log_range(repo, 'origin/develop', 'feature/1.2.0')
    assert commits[0]['sha'] == sha and commits[0]['subject'] == 'fix: demo bug#4336'
    assert commits[0]['author'] == 'demo-dev' and commits[0]['date']
    assert changed_files(repo, base, sha) == ['demo-module/a b.txt']
    assert status_porcelain(repo) == ''
    (repo / 'demo-untracked.txt').write_text('demo')
    assert 'demo-untracked.txt' in status_porcelain(repo)
    assert worktree_for_branch(repo, 'feature/1.2.0') == repo.resolve()
    assert worktree_for_branch(repo, 'develop') is None
    fixture.push()
    fetch(repo, 'feature/1.2.0', 'develop', 'master')
    assert ahead(repo, 'feature/1.2.0', 'origin/feature/1.2.0') == 0


def test_find_branch_in_secondary_worktree(git_repo, tmp_path):
    other = tmp_path / 'demo other worktree'
    git_repo.git(git_repo.work, 'worktree', 'add', str(other), 'develop')
    assert worktree_for_branch(git_repo.work, 'develop') == other.resolve()


def test_invocations_use_safe_subprocess_options(git_repo, monkeypatch):
    actual = subprocess.run
    calls = []

    def capture(args, **kwargs):
        calls.append((args, kwargs))
        return actual(args, **kwargs)

    monkeypatch.setattr('dce.loop.gitops.subprocess.run', capture)
    fetch(git_repo.work, 'develop')
    assert calls
    for args, kwargs in calls:
        assert isinstance(args, list) and args[0] == 'git'
        assert kwargs['shell'] is False and kwargs['timeout'] == 60
        assert kwargs['env']['GIT_TERMINAL_PROMPT'] == '0'


def test_git_failure_and_timeout_are_specific(git_repo, monkeypatch):
    with pytest.raises(DceError) as caught:
        log_range(git_repo.work, 'origin/develop', 'demo-missing')
    assert caught.value.code == ErrorCode.GIT_ERROR
    assert 'demo-missing' in caught.value.message and 'Git' in caught.value.message

    def fail(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 128, '', '\n'.join(map(str, range(25))))

    monkeypatch.setattr('dce.loop.gitops.subprocess.run', fail)
    with pytest.raises(DceError) as caught:
        fetch(git_repo.work, 'develop')
    assert '24' in caught.value.message and '\n0\n' not in caught.value.message

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 60)

    monkeypatch.setattr('dce.loop.gitops.subprocess.run', timeout)
    with pytest.raises(DceError, match='60') as caught:
        status_porcelain(git_repo.work)
    assert caught.value.code == ErrorCode.GIT_ERROR


def test_missing_git_and_unsafe_reference(git_repo, monkeypatch):
    with pytest.raises(DceError):
        fetch(git_repo.work, '--upload-pack=demo')

    def fail(*args, **kwargs):
        raise FileNotFoundError('demo git unavailable')

    monkeypatch.setattr('dce.loop.gitops.subprocess.run', fail)
    with pytest.raises(DceError, match='demo git unavailable'):
        run_git(git_repo.work, 'status', '--porcelain')
