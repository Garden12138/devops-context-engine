from pathlib import Path

import pytest

from dce.errors import DceError
from dce.workspace.ci_parser import parse_ci

FIXTURES = Path('tests/fixtures/ci')


def fixture(name, branch='develop'):
    return parse_ci((FIXTURES / name).read_text(), branch)


def test_child_trigger_selection():
    result = fixture('maven_root.yml')
    assert result.trigger_include == '.gitlab-ci-dev.yml'
    assert result.trigger_job == 'trigger_dev'
    assert result.branches_referenced == {'master', 'release', 'develop'}


def test_maven_templates_export_and_needs():
    result = fixture('maven_dev.yml')
    assert len(result.modules) == 2
    module = result.modules[0]
    assert vars(module) == dict(
        path='demo-modules/demo-order', kind='service', compile_job='compile_demo_order',
        build_job='build_demo_order', image='demo/demo-modules-order',
    )
    job = next(j for j in result.jobs if j.name == 'compile_demo_order')
    assert job.when_on_branch['develop'] == 'manual'
    assert fixture('maven_dev.yml', 'master').modules == []


def test_frontend_pairing_and_unpaired_warning():
    result = fixture('web.yml')
    assert len(result.modules) == 2
    module, other = result.modules
    assert module.path == '.' and module.kind == 'web'
    assert module.image == 'demo/demo-web' and module.compile_job == 'compile_demo_web'
    assert other.path is None and other.compile_job is None
    assert any('build_other_dev' in w for w in result.warnings)


def test_library_and_unknown_rule():
    module = fixture('library.yml').modules[0]
    assert module.kind == 'library' and module.compile_job == 'deploy_common_core'
    assert module.build_job is None and module.path == 'demo-common-core'
    unknown = fixture('unknown_rule.yml')
    assert any('$CI_PIPELINE_SOURCE == "web"' in w for w in unknown.warnings)
    assert unknown.modules == []


def test_three_level_merge_variable_priority_and_order():
    result = parse_ci('''
variables: {REPO: demo, NAME: demo-global}
.base:
  variables: {NAME: demo-base, KEEP: demo-kept}
  script: ["docker push $REGISTRY/$REPO/${NAME}:latest"]
.middle:
  extends: .base
  variables: {NAME: demo-middle}
.last:
  extends: [.base, .middle]
job:
  extends: .last
  variables: {NAME: demo-job}
''', 'develop')
    job = result.jobs[0]
    assert job.variables['KEEP'] == 'demo-kept'
    assert job.variables['NAME'] == 'demo-job'
    assert job.image_pushes == ['$REGISTRY/demo/demo-job:latest']
    assert result.modules[0].image == 'demo/demo-job'


@pytest.mark.parametrize('text', [
    'x' * (1024 * 1024 + 1), '[]', 'job: [',
    '.a: {extends: .b}\n.b: {extends: .a}\njob: {extends: .a}',
    'job: {extends: .missing}',
    'job: {script: [' + ','.join('x' for _ in range(26000)) + ']}',
    '\n'.join(f'.a{i}: {{extends: .a{i+1}}}' for i in range(6))
    + '\n.a6: {}\njob: {extends: .a0}',
])
def test_unsafe_or_unresolvable_yaml(text):
    with pytest.raises(DceError) as error:
        parse_ci(text, 'develop')
    assert error.value.code == 'CONFIG_INVALID'


def test_export_sequential_and_push_preferred_over_build():
    result = parse_ci('''
variables: {A: demo-one, NEXT: "${A}"}
job:
  script:
    - export A=demo-two
    - docker build -t registry.example.invalid/demo/$NEXT:old .
    - export A=demo-three
    - docker push registry.example.invalid/demo/$A:latest
''', 'develop')
    assert result.modules[0].image == 'demo/demo-three'
