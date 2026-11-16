import json

from dce.output import bounded, compact, success


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
