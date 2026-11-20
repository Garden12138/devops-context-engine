import json
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from dce.errors import DceError, ErrorCode
from dce.loop.runs import append_event, list_runs, load_run, new_run, save_run


def test_new_run_round_trip_and_unique_ids(tmp_path):
    run = new_run(tmp_path, [4336, 4327])
    assert re.fullmatch(r'\d{8}-\d{4}-4336-4327(?:-[a-f0-9]+)?', run['run_id'])
    save_run(tmp_path, run)
    assert load_run(tmp_path, run['run_id']) == run
    assert run['stage'] == 'planned'
    assert run['bugs'] == [{'id': 4336}, {'id': 4327}]
    assert new_run(tmp_path, [4336, 4327])['run_id'] != run['run_id']


@pytest.mark.parametrize('point', ['replace', 'dump'])
def test_failed_write_leaves_original_and_cleans_temporary_file(tmp_path, monkeypatch, point):
    run = new_run(tmp_path, [4336])
    save_run(tmp_path, run)
    path = tmp_path / '.dce/runs' / f"{run['run_id']}.json"
    original = path.read_bytes()
    run['stage'] = 'fixing'

    def fail(*args, **kwargs):
        if point == 'dump':
            args[1].write('{"partial":')
        raise OSError('demo disk write failure')

    monkeypatch.setattr(f'dce.loop.runs.{"os.replace" if point == "replace" else "json.dump"}',
                        fail)
    with pytest.raises(DceError, match='demo disk write failure'):
        save_run(tmp_path, run)
    assert path.read_bytes() == original
    assert sorted(p.suffix for p in path.parent.iterdir()) == ['.json', '.lock']


def test_concurrent_stale_snapshots_preserve_events_and_independent_updates(tmp_path):
    run = new_run(tmp_path, [4336])
    save_run(tmp_path, run)
    barrier = Barrier(2)

    def update(index):
        current = load_run(tmp_path, run['run_id'])
        current['builds'][str(index)] = {'status': 'success'}
        append_event(current, 'deploy_plan', 'plan', f'demo-{index}', 'ok', 'demo')
        barrier.wait(timeout=5)
        save_run(tmp_path, current)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(update, [1, 2]))
    stored = load_run(tmp_path, run['run_id'])
    assert {e['target'] for e in stored['events']} == {'demo-1', 'demo-2'}
    assert len(stored['events']) == 2
    assert set(stored['builds']) == {'1', '2'}
    save_run(tmp_path, stored)
    assert len(load_run(tmp_path, run['run_id'])['events']) == 2


def test_events_are_append_only(tmp_path):
    run = new_run(tmp_path, [4336])
    append_event(run, 'deploy_plan', 'plan', 'demo-cloud', 'ok', 'demo')
    save_run(tmp_path, run)
    current = load_run(tmp_path, run['run_id'])
    current['events'][0]['result'] = 'changed'
    with pytest.raises(DceError) as caught:
        save_run(tmp_path, current)
    assert caught.value.code == ErrorCode.PRECONDITION_FAILED
    assert load_run(tmp_path, run['run_id'])['events'][0]['result'] == 'ok'


def test_list_runs_sorted_by_updated_at(tmp_path):
    first, second = (new_run(tmp_path, [i]) for i in [4336, 4327])
    save_run(tmp_path, first)
    save_run(tmp_path, second)
    assert [r['run_id'] for r in list_runs(tmp_path)] == [second['run_id'], first['run_id']]
    save_run(tmp_path, first)
    assert list_runs(tmp_path)[0]['run_id'] == first['run_id']


@pytest.mark.parametrize('link', ['directory', 'json', 'lock'])
def test_run_paths_reject_symlinks(tmp_path, link):
    outside = tmp_path / 'demo-outside'
    outside.mkdir()
    run = new_run(tmp_path, [4336])
    directory = tmp_path / '.dce/runs'
    directory.mkdir(parents=True, exist_ok=True)
    if link == 'directory':
        directory.rmdir()
        directory.symlink_to(outside, target_is_directory=True)
    else:
        (directory / f"{run['run_id']}.{link}").symlink_to(outside / f'demo.{link}')
    with pytest.raises(DceError) as caught:
        save_run(tmp_path, run)
    assert caught.value.code == ErrorCode.OUT_OF_SCOPE
    assert list(outside.iterdir()) == []


def test_load_rejects_bad_snapshot_and_traversal(tmp_path):
    run = new_run(tmp_path, [4336])
    save_run(tmp_path, run)
    path = tmp_path / '.dce/runs' / f"{run['run_id']}.json"
    path.write_text(json.dumps({'run_id': 'wrong'}))
    with pytest.raises(DceError, match='run_id'):
        load_run(tmp_path, run['run_id'])
    with pytest.raises(DceError) as caught:
        load_run(tmp_path, '../demo')
    assert caught.value.code == ErrorCode.OUT_OF_SCOPE


def test_audit_stderr_redacts_target_and_omits_detail(tmp_path, capsys):
    run = new_run(tmp_path, [4336])
    append_event(run, 'deploy_plan', 'plan', 'Authorization: Bearer demo-secret',
                 'ok', 'demo private detail')
    output = capsys.readouterr().err
    assert 'demo-secret' not in output and 'demo private detail' not in output
    audit = json.loads(output)
    assert set(audit) == {'ts', 'request_id', 'tool', 'action', 'target', 'result', 'error_code'}
