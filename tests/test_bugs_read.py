from pathlib import Path

import httpx
import pytest
import yaml
from test_platform_migration import client

from dce.errors import DceError, ErrorCode
from dce.loop.bugs import get_bug, list_bugs
from dce.platforms.zentao import ZenTao
from dce.workspace.config import DceConfig


@pytest.fixture
def cfg():
    return DceConfig.model_validate(yaml.safe_load(Path('examples/dce.example.yaml').read_text()))


def bug(**extra):
    return {'id': 4336, 'product': 100, 'title': 'demo bug', 'status': 'active',
            'assignedTo': {'account': 'dev01'}, 'openedBy': {'account': 'tester01'},
            'openedDate': '2026-11-16 10:00', 'steps': '<p>demo steps</p>', **extra}


def test_product_checked_before_parsing_or_fetching_images(cfg, monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json=bug(product={'id': 200}, steps='<img src="/demo.png">'))

    monkeypatch.setattr(ZenTao, 'parse_steps', lambda _: pytest.fail('body parsed'))
    with client(handle) as http, pytest.raises(DceError) as caught:
        get_bug(cfg, 4336, client=ZenTao(http))
    assert caught.value.code == ErrorCode.OUT_OF_SCOPE
    assert '200' in caught.value.message and '4336' in caught.value.message
    assert [r.url.path for r in requests] == ['/api.php/v1/bugs/4336']


def test_six_of_eight_images_and_actions(cfg):
    requests = []

    def handle(request):
        requests.append(request)
        if request.url.path.endswith('/4336'):
            return httpx.Response(200, json=bug(
                product={'id': 100},
                steps=''.join(f'<img src="/file-read-{i}.png">' for i in range(8)),
                actions=[{'date': '2026-11-16', 'actor': 'tester01', 'action': 'activated',
                          'comment': 'demo reopened', 'extra': 'ignored'}],
            ))
        return httpx.Response(200, headers={'Content-Type': 'image/png'},
                              content=b'\x89PNG\r\n\x1a\n')

    with client(handle) as http:
        view, images = get_bug(cfg, 4336, client=ZenTao(http))
    assert len(images) == 6 and len(requests) == 7
    assert [i['delivered'] for i in view.data['images']] == [True] * 6 + [False] * 2
    assert view.data['images'][7]['name'] == 'file-read-7.png'
    assert view.data['history'] == [{'date': '2026-11-16', 'actor': 'tester01',
                                   'action': 'activated', 'comment': 'demo reopened'}]
    assert view.data['opened_by'] == 'tester01'


def test_bad_image_and_missing_history(cfg):
    def handle(request):
        if request.url.path.endswith('/4336'):
            return httpx.Response(200, json=bug(steps='<img src="/demo.png">'))
        return httpx.Response(200, headers={'Content-Type': 'image/png'}, content=b'GIF89a')

    with client(handle) as http:
        view, images = get_bug(cfg, 4336, client=ZenTao(http))
    assert images == [] and view.data['images'][0]['delivered'] is False
    assert view.data['history'] == []
    assert any(w['code'] == 'HISTORY_UNAVAILABLE' for w in view.warnings)
    assert 'demo.png' in view.summary


def test_images_disabled_and_limit(cfg):
    for enabled, maximum, count in [(False, 6, 0), (True, 0, 0), (True, 1, 1)]:
        requests = []

        def handle(request, requests=requests):
            requests.append(request)
            if request.url.path.endswith('/4336'):
                return httpx.Response(200, json=bug(steps='<img src="/demo.png">', actions=[]))
            return httpx.Response(200, headers={'Content-Type': 'image/png'},
                                  content=b'\x89PNG\r\n\x1a\n')

        with client(handle) as http:
            view, images = get_bug(cfg, 4336, enabled, maximum, client=ZenTao(http))
        assert len(images) == count and len(requests) == count + 1
        assert not view.warnings


def test_list_filters_pages_and_ten_page_cap(cfg):
    pages = []

    def handle(request):
        assert request.url.path == '/api.php/v1/products/100/bugs'
        assert request.url.params['limit'] == '100'
        page = int(request.url.params['page'])
        pages.append(page)
        return httpx.Response(200, json={'bugs': [
            bug(id=page * 100 + i, assignedTo={'account': 'dev01' if i % 2 else 'dev02'},
                status='resolved' if i == 1 else 'active') for i in range(100)
        ]})

    with client(handle) as http:
        view = list_bugs(cfg, 'mine', 'active', 600, client=ZenTao(http))
    assert len(view.data['bugs']) == 490
    assert pages == list(range(1, 11))
    assert view.warnings[0]['code'] == 'TRUNCATED'
    assert '| 103 |' in view.summary
    assert all(b['assigned_to'] == 'dev01' and b['status'] == 'active'
               for b in view.data['bugs'])


def test_list_all_limit_and_account_fallback(cfg):
    with client(lambda r: httpx.Response(200, json={'bugs': [bug(), bug(id=4327)]})) as http:
        cfg.zentao.account = None
        http.settings._zentao_account = 'dev01'
        assert len(list_bugs(cfg, 'mine', 'active', 1, client=ZenTao(http)).data['bugs']) == 1
        assert len(list_bugs(cfg, 'all', 'all', 20, client=ZenTao(http)).data['bugs']) == 2


@pytest.mark.parametrize('kwargs', [{'max_images': -1}, {'bug_id': 0}])
def test_bad_get_input(cfg, kwargs):
    with client(lambda r: pytest.fail('request')) as http, pytest.raises(DceError):
        get_bug(cfg, **{'bug_id': 4336, **kwargs}, client=ZenTao(http))
