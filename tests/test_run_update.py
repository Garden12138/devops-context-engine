import json
from pathlib import Path

import pytest
import yaml
from gitfixture import GitFixture
from test_config import write_config
from typer.testing import CliRunner

from dce.cli import app
from dce.loop.runs import new_run, save_run
from dce.mcp_server import Runtime


@pytest.fixture
def recording(tmp_path):
    fixture = GitFixture(tmp_path / 'demo-records')
    cfg = yaml.safe_load(Path('examples/dce.example.yaml').read_text())
    cfg['records'].update(repo='demo-pm', file='缺陷修复记录.md')
    next(repo for repo in cfg['repos'] if repo['name'] == 'demo-pm')['path'] = (
        str(fixture.work.relative_to(tmp_path))
    )
    write_config(tmp_path, cfg)
    record_file = cfg['records']['file']
    commit = fixture.commit(record_file, '# demo records\n', 'docs: record bug#4336')
    run = new_run(tmp_path, [4336, 4327])
    run['stage'] = 'deployed'
    save_run(tmp_path, run)
    runtime = Runtime(workspace=tmp_path, credentials=tmp_path / 'missing.env')
    return runtime, run['run_id'], {'file': record_file, 'commit': commit}


@pytest.mark.parametrize('evidence', ['../outside.png', 'demo-missing.png', 'demo-link.png', '.'])
def test_rejects_evidence_without_partial_write(recording, tmp_path, evidence):
    runtime, run_id, record = recording
    (tmp_path / 'demo-link.png').symlink_to(tmp_path.parent / 'outside.png')
    before = (tmp_path / f'.dce/runs/{run_id}.json').read_bytes()
    result = runtime.call('run_update', run_id=run_id, record=record, verification={
        'bug_id': 4336, 'result': 'passed', 'notes': 'demo', 'evidence': [evidence],
    })
    assert result['error']['code'] == ('OUT_OF_SCOPE' if evidence in {
        '../outside.png', 'demo-link.png',
    } else 'PRECONDITION_FAILED')
    assert evidence in result['error']['message'] or evidence == '.'
    assert (tmp_path / f'.dce/runs/{run_id}.json').read_bytes() == before


def test_rejects_missing_commit_and_non_commit_object(recording, tmp_path):
    runtime, run_id, record = recording
    blob = GitFixture.git(tmp_path / 'demo-records/demo-work', 'rev-parse', 'HEAD:README.md')
    for commit in ('0123456789abcdef', blob):
        result = runtime.call('run_update', run_id=run_id, record={**record, 'commit': commit})
        assert result['error']['code'] == 'PRECONDITION_FAILED'
        assert 'demo-pm' in result['error']['message']
        assert commit in result['error']['message']


def test_verification_stage_and_cli_record_are_persisted(recording, tmp_path):
    runtime, run_id, record = recording
    evidence = tmp_path / 'demo-evidence.png'
    evidence.touch()

    def verify(bug_id, result):
        assert runtime.call('run_update', run_id=run_id, verification={
            'bug_id': bug_id, 'result': result, 'notes': 'demo', 'evidence': [evidence.name],
        })['ok']
        return runtime.call('dce_status', run_id=run_id)['data']['run']

    assert verify(4336, 'failed')['stage'] == 'fixing'
    assert verify(4327, 'passed')['stage'] == 'fixing'
    run = verify(4336, 'passed')
    assert run['stage'] == 'verified'
    assert run['verifications']['4336']['evidence'] == [evidence.name]
    assert run['verifications']['4336']['at']
    result = CliRunner().invoke(app, ['--workspace', str(tmp_path), 'run', 'update',
                                     '--run', run_id, '--file', record['file'], '--commit',
                                     record['commit'][:7], '--note', 'demo done'])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['ok']
    run = runtime.call('dce_status', run_id=run_id)['data']['run']
    assert run['stage'] == 'recorded'
    assert run['record']['commit'] == record['commit'][:7]
    assert run['record']['at']
    assert any(e['action'] == 'note' and e['detail'] == 'demo done' for e in run['events'])


def test_empty_update_and_bug_outside_run(recording):
    runtime, run_id, _ = recording
    assert runtime.call('run_update', run_id=run_id)['error']['code'] == 'CONFIG_INVALID'
    result = runtime.call('run_update', run_id=run_id, verification={
        'bug_id': 4300, 'result': 'passed', 'notes': 'demo', 'evidence': [],
    })
    assert result['error']['code'] == 'OUT_OF_SCOPE'
