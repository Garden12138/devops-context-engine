import json

import pytest

from dce.output import bounded, check_output, compact, success
from dce.workspace.doctor import Check


def test_large_lists_are_bounded_and_report_removed_count():
    payload = bounded(success('demo list', {'jobs': [
        {'name': f'demo-{index}', 'detail': 'demo ' * 50} for index in range(500)
    ]}))
    assert len(compact(payload).encode()) <= 24000
    assert payload['warnings'][0]['code'] == 'TRUNCATED'
    count = 500 - len(payload['data']['jobs'])
    assert str(count) in payload['warnings'][0]['message']


def test_large_run_retains_recent_twenty_events():
    events = [{'index': index, 'detail': 'demo ' * 70} for index in range(100)]
    payload = bounded(success('demo run', {'run': {'events': events}}))
    assert payload['data']['run']['events'] == events[-20:]
    assert '80' in payload['warnings'][0]['message']


def test_sensitive_output_and_oversized_scalar_are_bounded():
    payload = bounded(success('demo', {'note': '演示' * 24000,
                                      'text': 'Authorization: Bearer demo-secret'}))
    assert len(compact(payload).encode()) <= 24000
    assert 'demo-secret' not in json.dumps(payload)
    assert payload['warnings'][0]['code'] == 'TRUNCATED'


@pytest.mark.parametrize('with_failure', [False, True])
def test_large_check_preserves_warnings_and_failures(with_failure):
    checks = [Check(f'repo.demo-cloud.job.compile_demo_{index}', 'pass',
                    f'GitLab 仓库 demo-cloud: compile_demo_{index} 在测试分支 CI 中存在')
              for index in range(337)]
    checks.insert(9, Check('gitlab.token_scope', 'warn',
                          'GitLab /personal_access_tokens/self HTTP 404: 无法读取 scopes。',
                          '在 GitLab 令牌设置中确认 api scope。'))
    checks.extend([Check('portainer.write', 'warn', '写权限需首次部署时验证'),
                   Check('zentao.resolve', 'warn', '解决权限需首次使用时验证')])
    if with_failure:
        checks.append(Check('repo.demo-cloud.job.demo_missing_job', 'fail',
                            'GitLab 仓库 demo-cloud HTTP 200: .gitlab-ci-dev.yml '
                            '找不到 demo_missing_job。', '更正 compile_job。'))
    payload = bounded(check_output(checks))
    assert len(compact(payload).encode()) <= 24000
    assert payload['data']['passed'] is not with_failure
    assert any(w['code'] == 'TRUNCATED' for w in payload['warnings'])
    retained = {item['id']: item for item in payload['data']['checks']}
    important = {item.id for item in checks if item.status != 'pass'}
    assert important.issubset(retained)
    for item in checks:
        if item.status != 'pass':
            assert retained[item.id]['detail'] == item.detail
            if item.fix:
                assert retained[item.id]['fix'] == item.fix
    assert len(payload['data']['checks']) < len(checks)
    assert all(item.status == 'pass' for item in checks if item.id not in retained)
