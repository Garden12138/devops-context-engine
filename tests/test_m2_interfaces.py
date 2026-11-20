import asyncio
import base64
import json
from pathlib import Path

import httpx
import pytest
import yaml
from mcp.types import ImageContent
from test_bugs_read import bug
from test_config import write_config
from test_plan import plan_workspace
from test_platform_migration import client
from typer.testing import CliRunner

from dce.cli import app
from dce.loop.runs import save_run
from dce.mcp_server import Runtime, create_server
from dce.settings import Settings

plan_workspace = plan_workspace


@pytest.fixture
def bug_runtime(tmp_path, monkeypatch):
    write_config(tmp_path, yaml.safe_load(Path('examples/dce.example.yaml').read_text()))
    requests = []
    png = b'\x89PNG\r\n\x1a\ndemo'

    def handle(request):
        requests.append(request)
        if request.url.path.endswith('/bugs'):
            return httpx.Response(200, json={'bugs': [bug()]})
        if request.url.path.endswith('/4336'):
            return httpx.Response(200, json=bug(
                steps='<p>demo screenshot</p><img src="/demo.png">'))
        if request.url.path.endswith('/4327'):
            return httpx.Response(200, json=bug(
                id=4327, product=200, steps='<img src="/demo.png">'))
        return httpx.Response(200, headers={'Content-Type': 'image/png'}, content=png)

    with client(handle) as http:
        settings = Settings(zentao=http.config)
    monkeypatch.setattr('dce.mcp_server.load_settings', lambda *args: settings)
    monkeypatch.setattr('dce.mcp_server.PlatformClient', lambda *args: client(handle))
    return tmp_path, requests, png


def test_mcp_native_image_and_scope_error(bug_runtime):
    ws, requests, png = bug_runtime

    async def exercise():
        server = create_server(workspace=ws)
        result = await server.call_tool('bug_get', {'bug_id': 4336})
        assert json.loads(result.content[0].text) == result.structuredContent
        assert result.structuredContent['ok'], result
        image, = [c for c in result.content if isinstance(c, ImageContent)]
        assert image.mimeType == 'image/png' and base64.b64decode(image.data) == png
        assert result.structuredContent['data']['images'][0]['delivered'] is True
        assert result.structuredContent['warnings'][0]['code'] == 'HISTORY_UNAVAILABLE'
        requests.clear()
        result = await server.call_tool('bug_get', {'bug_id': 4327})
        assert result.isError and result.structuredContent['error']['code'] == 'OUT_OF_SCOPE'
        assert len(requests) == 1 and len(result.content) == 1
        assert 'steps_text' not in json.dumps(result.structuredContent)

    asyncio.run(exercise())


def test_bug_list_run_link_and_cli_save_images(bug_runtime):
    ws, requests, png = bug_runtime
    from dce.loop.runs import new_run
    run = new_run(ws, [4336])
    save_run(ws, run)
    payload = Runtime(workspace=ws).call('bug_list')
    assert payload['ok'] and payload['data']['bugs'][0]['run_id'] == run['run_id']
    assert Runtime(workspace=ws).call('bug_get', bug_id=4336)['data']['run_id'] == run['run_id']
    runner = CliRunner()
    prefix = ['--workspace', str(ws)]
    listed = runner.invoke(app, [*prefix, 'bug', 'list', '--all', '--status', 'active'])
    assert listed.exit_code == 0 and json.loads(listed.stdout)['data']['bugs'][0]['id'] == 4336
    images = ws / 'demo-images'
    shown = runner.invoke(app, [*prefix, 'bug', 'show', '4336', '--save-images', str(images)])
    assert shown.exit_code == 0, shown.output
    assert [p.read_bytes() for p in images.iterdir()] == [png]
    requests.clear()
    shown = runner.invoke(app, [*prefix, 'bug', 'show', '4336'])
    assert shown.exit_code == 0 and len(requests) == 1
    denied = runner.invoke(app, [*prefix, 'bug', 'show', '4327'])
    assert denied.exit_code == 1
    assert json.loads(denied.stdout)['error']['code'] == 'OUT_OF_SCOPE'


def test_plan_cli_json_pretty_and_refresh_without_credentials(plan_workspace):
    ws, cfg, fixtures = plan_workspace
    fixtures['demo-web'].commit('src/demo.js', 'demo', 'fix: bug#4336')
    runner = CliRunner()
    args = ['--workspace', str(ws), '--credentials', str(ws / 'missing.env')]
    result = runner.invoke(app, [*args, 'plan', '4336', '--repo', 'demo-web'])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data['data']['items'][0]['id'] == 'demo-web:.'
    result = runner.invoke(app, [*args, '--pretty', 'plan', '4336',
                                 '--run', data['data']['run_id']])
    assert result.exit_code == 0 and result.stdout.startswith('| 顺序 | 仓库 |')


def test_invalid_cli_bug_filter_and_image_destination(bug_runtime):
    ws, requests, png = bug_runtime
    runner = CliRunner()
    args = ['--workspace', str(ws)]
    result = runner.invoke(app, [*args, 'bug', 'list', '--status', 'demo-invalid'])
    assert result.exit_code == 1
    assert json.loads(result.stdout)['error']['code'] == 'CONFIG_INVALID'
    target = ws / 'demo-file'
    target.write_text('demo')
    result = runner.invoke(app, [*args, 'bug', 'show', '4336', '--save-images', str(target)])
    assert result.exit_code == 1
    assert 'demo-file' in json.loads(result.stdout)['error']['message']
