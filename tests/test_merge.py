from pathlib import Path

import pytest
import yaml
from gitfixture import GitFixture

from dce.errors import DceError, ErrorCode
from dce.loop import gitops
from dce.loop.runs import load_run, new_run, save_run
from dce.workspace.config import DceConfig


@pytest.fixture
def setup(tmp_path, monkeypatch):
    f = GitFixture(tmp_path / 'demo-fixture')
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', '/dev/null')
    monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')
    for key, value in [('user.name', 'demo-dev'), ('user.email', 'demo@example.invalid'),
                       ('commit.gpgsign', 'false'), ('core.hooksPath', '/dev/null')]:
        f.git(f.work, 'config', key, value)
    cfg = DceConfig.model_validate(yaml.safe_load(Path('examples/dce.example.yaml').read_text()))
    repo = cfg.repos[2]
    repo.path = str(f.work.relative_to(tmp_path))
    cfg.repos = [repo]
    f.commit('src/demo.js', 'demo feature\n', 'fix: demo bug#4336')
    run = new_run(tmp_path, [4336])
    run['feature_branches'] = {repo.name: 'feature/1.2.0'}
    run['plan'] = {'items': [{'id': 'demo-web:.', 'repo': repo.name}]}
    save_run(tmp_path, run)
    original = gitops.run_git
    calls = []

    def capture(path, *args, **kwargs):
        calls.append((path, args))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(gitops, 'run_git', capture)
    yield tmp_path, cfg, repo, run, f, calls
    assert all('--force' not in args and '-f' not in args for _, args in calls)
    assert not list((tmp_path / '.dce/tmp').glob('merge-*'))


def test_merge_preserves_user_checkout_and_records_success(setup):
    ws, cfg, repo, run, f, calls = setup
    head = f.git(f.work, 'rev-parse', 'HEAD')
    result = gitops.merge_repo(ws, cfg, run, repo, True)
    assert result['status'] == 'merged'
    merged = f.git(f.origin, 'rev-parse', 'develop')
    parents = f.git(f.origin, 'show', '-s', '--format=%P', merged).split()
    assert len(parents) == 2 and parents[1] == head
    assert 'bug#4336' in f.git(f.origin, 'show', '-s', '--format=%s', merged)
    assert f.git(f.work, 'rev-parse', 'HEAD') == head
    assert f.git(f.work, 'branch', '--show-current') == 'feature/1.2.0'
    assert (f.work / 'src/demo.js').read_text() == 'demo feature\n'
    assert f.git(f.work, 'status', '--porcelain') == ''
    assert load_run(ws, run['run_id'])['merges'][repo.name]['merge_sha'] == merged
    assert any(a[:3] == ('worktree', 'add', '--detach') for _, a in calls)
    assert gitops.merge_repo(ws, cfg, run, repo, True)['status'] == 'already_merged'


def test_conflict_aborts_and_leaves_origin_and_user_unchanged(setup):
    ws, cfg, repo, run, f, calls = setup
    f.checkout('develop')
    f.commit('src/demo.js', 'demo test branch\n', 'chore: demo conflict')
    f.push('develop')
    f.checkout('feature/1.2.0')
    old = f.git(f.origin, 'rev-parse', 'develop')
    head = f.git(f.work, 'rev-parse', 'HEAD')
    result = gitops.merge_repo(ws, cfg, run, repo, True)
    assert result['status'] == 'conflict' and result['files'] == ['src/demo.js']
    assert result['error']['code'] == 'GIT_CONFLICT'
    assert f.git(f.origin, 'rev-parse', 'develop') == old
    assert f.git(f.work, 'rev-parse', 'HEAD') == head
    assert any(a == ('merge', '--abort') for _, a in calls)


@pytest.mark.parametrize('case,code', [('approval', 'PRECONDITION_FAILED'),
    ('dirty', 'GIT_DIRTY'), ('plan', 'PRECONDITION_FAILED'), ('on_test', 'PRECONDITION_FAILED')])
def test_preconditions_reject_without_push(setup, case, code):
    ws, cfg, repo, run, f, calls = setup
    if case == 'dirty':
        (f.work / 'demo-dirty.txt').write_text('demo')
    elif case == 'plan':
        run['plan'] = {}
    elif case == 'on_test':
        f.checkout('develop')
        f.commit('demo-local.txt', 'demo', 'chore: demo local test commit')
    result = gitops.merge_repo(ws, cfg, run, repo, case != 'approval')
    assert result['status'] == 'rejected' and result['error']['code'] == code
    assert all(a[0] != 'push' for _, a in calls)


def test_tampered_protected_branch_raises_out_of_scope(setup):
    ws, cfg, repo, run, f, calls = setup
    repo.test_branch = 'master'
    with pytest.raises(DceError) as exc:
        gitops.merge_repo(ws, cfg, run, repo, True)
    assert exc.value.code == ErrorCode.OUT_OF_SCOPE
    assert calls == []


def test_racing_test_push_remerges_once(setup, monkeypatch):
    ws, cfg, repo, run, f, calls = setup
    peer = ws / 'demo-peer'
    f.git(ws, 'clone', str(f.origin), str(peer))
    actual = gitops.run_git
    pushes = []

    def racing(path, *args, **kwargs):
        if args == ('push', 'origin', 'HEAD:refs/heads/develop'):
            pushes.append(args)
            if len(pushes) == 1:
                f.git(peer, 'checkout', 'develop')
                (peer / 'demo-race.txt').write_text('demo')
                f.git(peer, 'add', 'demo-race.txt')
                f.git(peer, 'commit', '-m', 'chore: demo concurrent update')
                f.git(peer, 'push', 'origin', 'develop:refs/heads/develop')
        return actual(path, *args, **kwargs)

    monkeypatch.setattr(gitops, 'run_git', racing)
    assert gitops.merge_repo(ws, cfg, run, repo, True)['status'] == 'merged'
    assert len(pushes) == 2
    assert f.git(f.origin, 'show', 'develop:demo-race.txt') == 'demo'


def test_feature_push_rejected_is_specific(setup):
    ws, cfg, repo, run, f, calls = setup
    peer = ws / 'demo-peer'
    f.git(ws, 'clone', str(f.origin), str(peer))
    f.git(peer, 'checkout', 'feature/1.2.0')
    (peer / 'demo-peer.txt').write_text('demo')
    f.git(peer, 'add', 'demo-peer.txt')
    f.git(peer, 'commit', '-m', 'chore: demo remote feature')
    f.git(peer, 'push', 'origin', 'feature/1.2.0:refs/heads/feature/1.2.0')
    result = gitops.merge_repo(ws, cfg, run, repo, True)
    assert result['status'] == 'push_rejected'
    assert result['error']['code'] == 'GIT_PUSH_REJECTED'
    assert 'feature/1.2.0' in result['error']['message']


def test_two_push_rejections_stop_after_one_retry(setup, monkeypatch):
    import subprocess

    ws, cfg, repo, run, f, calls = setup
    actual = gitops.run_git
    pushes = []

    def reject(path, *args, **kwargs):
        if args == ('push', 'origin', 'HEAD:refs/heads/develop'):
            pushes.append(args)
            return subprocess.CompletedProcess(['git', *args], 1, '', 'demo non-fast-forward')
        return actual(path, *args, **kwargs)

    old = f.git(f.origin, 'rev-parse', 'develop')
    head = f.git(f.work, 'rev-parse', 'HEAD')
    monkeypatch.setattr(gitops, 'run_git', reject)
    result = gitops.merge_repo(ws, cfg, run, repo, True)
    assert result['status'] == 'push_rejected' and len(pushes) == 2
    assert f.git(f.origin, 'rev-parse', 'develop') == old
    assert f.git(f.work, 'rev-parse', 'HEAD') == head


def test_other_user_checkout_and_dirty_files_are_untouched(setup):
    ws, cfg, repo, run, f, calls = setup
    feature_tree = ws / 'demo-feature-tree'
    f.checkout('master')
    f.git(f.work, 'worktree', 'add', str(feature_tree), 'feature/1.2.0')
    (f.work / 'demo-local.txt').write_text('demo keep')
    head = f.git(f.work, 'rev-parse', 'HEAD')
    assert gitops.merge_repo(ws, cfg, run, repo, True)['status'] == 'merged'
    assert f.git(f.work, 'rev-parse', 'HEAD') == head
    assert f.git(f.work, 'branch', '--show-current') == 'master'
    assert (f.work / 'demo-local.txt').read_text() == 'demo keep'
