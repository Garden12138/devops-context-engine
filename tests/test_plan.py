from pathlib import Path

import pytest
import yaml
from gitfixture import GitFixture

from dce.errors import DceError, ErrorCode
from dce.loop.plan import make_plan
from dce.loop.runs import load_run
from dce.output import plan_output
from dce.workspace.config import DceConfig, dump_config


@pytest.fixture
def plan_workspace(tmp_path):
    cfg = DceConfig.model_validate(yaml.safe_load(Path('examples/dce.example.yaml').read_text()))
    cfg.repos = [r for r in cfg.repos if r.modules]
    fixtures = {}
    for repo in cfg.repos:
        fixture = GitFixture(tmp_path / f'{repo.name}-fixture')
        fixture.work.rename(tmp_path / repo.name)
        fixture.work = tmp_path / repo.name
        repo.test_branch = 'develop'
        fixtures[repo.name] = fixture
    (tmp_path / '.dce').mkdir()
    (tmp_path / '.dce/dce.yaml').write_text(dump_config(cfg))
    return tmp_path, cfg, fixtures


def codes(run):
    return {w['code'] for w in run['plan']['warnings']}


def test_service_mapping_commits_and_missing_bug(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    sha = fixtures['demo-cloud'].commit('demo-modules/demo-order/src/A.java', 'demo',
                                       'fix: demo order bug#4336')
    before = fixtures['demo-cloud'].git(fixtures['demo-cloud'].work, 'rev-parse', 'HEAD')
    run = make_plan(ws, cfg, [4336, 4327])
    item, = run['plan']['items']
    assert item == {'id': 'demo-cloud:demo-modules/demo-order', 'repo': 'demo-cloud',
                    'module': 'demo-modules/demo-order', 'kind': 'service', 'reason': 'changed',
                    'bugs': [4336], 'required': True, 'compile_job': 'compile_demo_order',
                    'build_job': 'build_demo_order', 'image': 'demo/demo-modules-order',
                    'services': ['demo_test_demo-modules-order']}
    assert run['plan']['commits']['demo-cloud'] == [
        {'sha': sha, 'subject': 'fix: demo order bug#4336', 'bugs': [4336]},
    ]
    assert run['plan']['bugs_without_commits'] == [4327]
    assert {'UNPUSHED', 'BUGS_WITHOUT_COMMITS'} <= codes(run)
    assert load_run(ws, run['run_id']) == run
    assert fixtures['demo-cloud'].git(fixtures['demo-cloud'].work, 'rev-parse', 'HEAD') == before


def test_web_root_module_and_unmapped_pom(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    fixtures['demo-web'].commit('src/demo.js', 'demo', 'fix: demo bug#4336')
    fixtures['demo-cloud'].commit('pom.xml', '<project/>', 'fix: demo pom bug#4336')
    run = make_plan(ws, cfg, [4336])
    assert run['plan']['items'][0]['id'] == 'demo-web:.'
    assert run['plan']['unmapped'] == {'demo-cloud': ['pom.xml']}
    assert 'UNMAPPED_CHANGES' in codes(run)


def test_library_downstream_order_and_table(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    fixtures['demo-common'].commit('demo-common-core/src/Common.java', 'demo', 'fix: bug#4336')
    run = make_plan(ws, cfg, [4336], repos=['demo-common'])
    library, service = run['plan']['items']
    assert library['kind'] == 'library' and library['required'] is True
    assert service['required'] is False
    assert service['reason'] == 'depends_on:com.demo:demo-common-core'
    assert service['bugs'] == [4336]
    assert run['plan']['order'] == ['demo-common:demo-common-core',
                                   'demo-cloud:demo-modules/demo-order']
    result = plan_output(run, cfg)
    assert result['summary'].splitlines()[0] == (
        '| 顺序 | 仓库 | 合并 | 编译 job | 构建 job | 镜像 | 服务 | 原因 | 缺陷 |'
    )
    assert 'feature/1.2.0 → develop' in result['summary'] and '建议重编' in result['summary']
    assert result['data']['run_id'] == run['run_id'] and result['warnings']


def test_dirty_and_commits_on_test_branch(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    fixture = fixtures['demo-web']
    fixture.commit('src/demo.js', 'demo', 'fix: bug#4336')
    (fixture.work / 'demo-dirty.txt').write_text('demo')
    run = make_plan(ws, cfg, [4336], repos=['demo-web'])
    assert 'DIRTY' in codes(run)
    (fixture.work / 'demo-dirty.txt').unlink()
    fixture.checkout('develop')
    fixture.commit('demo-on-test.txt', 'demo', 'fix: demo on test bug#4336')
    run = make_plan(ws, cfg, [4336], repos=['demo-web'])
    assert 'COMMITTED_ON_TEST_BRANCH' in codes(run)


def test_feature_worktree_dirty_in_other_checkout(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    fixture = fixtures['demo-web']
    fixture.commit('src/demo.js', 'demo', 'fix: bug#4336')
    fixture.checkout('master')
    other = ws / 'demo-secondary'
    fixture.git(fixture.work, 'worktree', 'add', str(other), 'feature/1.2.0')
    (other / 'demo.txt').write_text('demo dirty')
    assert 'DIRTY' in codes(make_plan(ws, cfg, [4336], repos=['demo-web']))


def test_test_branch_merge_pollution(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    fixture = fixtures['demo-web']
    fixture.checkout('develop')
    fixture.commit('src/from-test.js', 'demo test', 'fix: demo test')
    fixture.push('develop')
    fixture.checkout('feature/1.2.0')
    fixture.commit('src/demo.js', 'demo feature', 'fix: bug#4336')
    fixture.git(fixture.work, 'merge', '--no-ff', 'develop', '-m', 'merge demo test')
    assert 'TEST_BRANCH_MERGED_INTO_FEATURE' in codes(
        make_plan(ws, cfg, [4336], repos=['demo-web']),
    )


def test_master_missing_skips_pollution_check(tmp_path):
    fixture = GitFixture(tmp_path / 'demo-fixture', initial='main')
    cfg = DceConfig.model_validate(yaml.safe_load(Path('examples/dce.example.yaml').read_text()))
    repo = next(r for r in cfg.repos if r.name == 'demo-web')
    cfg.repos = [repo]
    repo.path = 'demo-fixture/demo-work'
    fixture.commit('src/demo.js', 'demo', 'fix: bug#4336')
    run = make_plan(tmp_path, cfg, [4336])
    assert 'TEST_BRANCH_MERGED_INTO_FEATURE' not in codes(run)


def test_add_drop_refresh_preserves_progress(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    fixtures['demo-cloud'].commit('demo-modules/demo-order/a.txt', 'demo', 'fix: bug#4336')
    run = make_plan(ws, cfg, [4336])
    run['builds']['demo'] = {'status': 'success'}
    from dce.loop.runs import save_run
    save_run(ws, run)
    result = make_plan(ws, cfg, [4336], run_id=run['run_id'], add_items=[
        {'repo': 'demo-web', 'module': '.', 'reason': '共享枚举改动'},
    ], drop_items=['demo-cloud:demo-modules/demo-order'])
    assert result['run_id'] == run['run_id']
    assert [i['id'] for i in result['plan']['items']] == ['demo-web:.']
    assert result['plan']['items'][0]['reason'] == '共享枚举改动'
    assert len(result['events']) == 2 and result['builds']['demo']['status'] == 'success'


def test_build_order_and_longest_module_prefix(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    cloud = next(r for r in cfg.repos if r.name == 'demo-cloud')
    nested = cloud.modules[0].model_copy(deep=True)
    nested.path += '/demo-nested'
    nested.compile_job = 'compile_demo_nested'
    cloud.modules.append(nested)
    fixtures['demo-cloud'].commit('demo-modules/demo-order/demo-nested/a', 'demo', 'fix: bug#4336')
    fixtures['demo-web'].commit('demo.js', 'demo', 'fix: bug#4336')
    cfg.build_order = ['demo-web', 'demo-cloud']
    run = make_plan(ws, cfg, [4336])
    assert run['plan']['order'] == ['demo-web:.', 'demo-cloud:demo-modules/demo-order/demo-nested']


def test_feature_override_and_no_change_skip(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    fixture = fixtures['demo-web']
    fixture.branch('feature/demo-override')
    fixture.commit('demo.js', 'demo', 'fix: bug#4336')
    fixture.push('feature/demo-override')
    run = make_plan(ws, cfg, [4336], feature_branches={'demo-web': 'feature/demo-override'})
    assert run['feature_branches']['demo-web'] == 'feature/demo-override'
    assert list(run['plan']['commits']) == ['demo-web']
    assert 'UNPUSHED' not in codes(run)


@pytest.mark.parametrize('args', [
    {'repos': ['demo-unknown']}, {'feature_branches': {'demo-unknown': 'feature/demo'}},
    {'add_items': [{'repo': 'demo-web', 'module': 'demo-unknown', 'reason': 'demo'}]},
    {'drop_items': ['demo-unknown:.']}, {'bug_ids': []},
    {'feature_branches': {'demo-web': '--upload-pack=demo'}},
])
def test_invalid_targets_rejected(plan_workspace, args):
    ws, cfg, fixtures = plan_workspace
    with pytest.raises(DceError) as caught:
        make_plan(ws, cfg, **{'bug_ids': [4336], **args})
    assert caught.value.code in {ErrorCode.OUT_OF_SCOPE, ErrorCode.CONFIG_INVALID,
                                 ErrorCode.GIT_ERROR}


def test_manual_library_and_transitive_downstream(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    cloud = next(r for r in cfg.repos if r.name == 'demo-cloud')
    cfg.repos[0].modules.append(cfg.repos[0].modules[0].model_copy(update={
        'path': 'demo-common-extra', 'artifact': 'com.demo:demo-common-extra',
        'uses': ['com.demo:demo-common-core'],
    }))
    cloud.modules[0].uses = ['com.demo:demo-common-extra']
    run = make_plan(ws, cfg, [4336], add_items=[
        {'repo': 'demo-common', 'module': 'demo-common-core', 'reason': 'demo shared change'},
    ])
    assert run['plan']['order'] == ['demo-common:demo-common-core',
                                   'demo-common:demo-common-extra',
                                   'demo-cloud:demo-modules/demo-order']


def test_dependency_cycle_is_specific(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    common = cfg.repos[0].modules[0]
    common.uses = ['com.demo:demo-modules-order']
    with pytest.raises(DceError, match='依赖环'):
        make_plan(ws, cfg, [4336], add_items=[
            {'repo': 'demo-common', 'module': common.path, 'reason': 'demo cycle'},
        ])
