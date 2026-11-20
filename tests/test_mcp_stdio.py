import asyncio
import json
import os
from pathlib import Path

import yaml
from gitfixture import GitFixture
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from test_config import write_config

from dce.loop.runs import new_run, save_run

TOOLS = {
    'project_setup', 'dce_status', 'bug_list', 'bug_get', 'deploy_plan', 'merge_to_test',
    'ci_build', 'ci_status', 'service_deploy', 'service_status', 'run_update', 'bug_resolve',
}
def test_stdio_lists_twelve_tools_and_reads_status_offline(tmp_path):
    import yaml

    write_config(tmp_path, yaml.safe_load(Path('examples/dce.example.yaml').read_text()))
    root = Path.cwd()

    async def exercise():
        parameters = StdioServerParameters(
            command=str(root / '.venv/bin/dce'), args=[
                'mcp', '--workspace', str(tmp_path),
                '--connections', str(tmp_path / 'missing-connections.toml'),
                '--credentials', str(tmp_path / 'missing-credentials.env'),
            ], env={**os.environ, 'PYTHONPATH': str(root / 'src')},
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listing = await session.list_tools()
                assert {tool.name for tool in listing.tools} == TOOLS
                for tool in listing.tools:
                    assert 'workspace' in tool.inputSchema['properties']
                    assert len(tool.description) <= 300
                result = await session.call_tool('dce_status', {})
                data = json.loads(result.content[0].text)
                assert data == result.structuredContent
                assert data['ok'] and data['data']['config']['repos'] == 4
                assert data['data']['runs'] == []
                run = new_run(tmp_path, [4336])
                save_run(tmp_path, run)
                updated = await session.call_tool(
                    'run_update', {'run_id': run['run_id'], 'note': 'demo'},
                )
                assert json.loads(updated.content[0].text) == updated.structuredContent
                assert updated.structuredContent['ok']
                mismatch = await session.call_tool(
                    'dce_status', {'workspace': str(tmp_path.parent)},
                )
                assert mismatch.structuredContent['error']['code'] == 'WORKSPACE_MISMATCH'
                missing = await session.call_tool('bug_resolve', {'run_id': 'demo-missing'})
                assert json.loads(missing.content[0].text) == missing.structuredContent
                assert missing.structuredContent['error']['code'] == 'NOT_FOUND'
                invalid = await session.call_tool('service_status', {})
                assert json.loads(invalid.content[0].text) == invalid.structuredContent
                assert invalid.structuredContent['error']['code'] == 'CONFIG_INVALID'
                for name, arguments in [
                    ('service_deploy', {'run_id': 'demo-run'}),
                    ('service_status', {'service': 'demo_test_demo-web', 'wait_seconds': 0}),
                ]:
                    unavailable = await session.call_tool(name, arguments)
                    assert json.loads(unavailable.content[0].text) == unavailable.structuredContent
                    assert unavailable.structuredContent['error']['code'] == 'CREDENTIALS_INVALID'

    asyncio.run(asyncio.wait_for(exercise(), timeout=20))


def test_stdio_deploy_plan_with_local_bare_origin_only(tmp_path):
    fixture = GitFixture(tmp_path / 'demo-fixture')
    cfg = yaml.safe_load(Path('examples/dce.example.yaml').read_text())
    repo = next(r for r in cfg['repos'] if r['name'] == 'demo-web')
    repo['path'] = 'demo-fixture/demo-work'
    cfg['repos'] = [repo]
    write_config(tmp_path, cfg)
    fixture.commit('src/demo.js', 'demo fix', 'fix: demo bug#4336')
    for key, value in [('user.name', 'demo-dev'), ('user.email', 'demo@example.invalid'),
                       ('commit.gpgsign', 'false'), ('core.hooksPath', '/dev/null')]:
        fixture.git(fixture.work, 'config', key, value)
    head = fixture.git(fixture.work, 'rev-parse', 'HEAD')
    root = Path.cwd()

    async def exercise():
        parameters = StdioServerParameters(
            command=str(root / '.venv/bin/dce'), args=[
                'mcp', '--workspace', str(tmp_path),
                '--connections', str(tmp_path / 'missing-connections.toml'),
                '--credentials', str(tmp_path / 'missing-credentials.env'),
            ], env={**os.environ, 'PYTHONPATH': str(root / 'src')},
        )
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool('deploy_plan', {'bug_ids': [4336]})
                data = json.loads(result.content[0].text)
                assert data == result.structuredContent
                assert data['ok'], data
                assert data['data']['items'][0]['id'] == 'demo-web:.'
                assert 'compile_demo_web' in data['summary']
                refreshed = await session.call_tool('deploy_plan', {
                    'bug_ids': [4336], 'run_id': data['data']['run_id'],
                })
                assert refreshed.structuredContent['data']['run_id'] == data['data']['run_id']
                status = await session.call_tool('dce_status', {'run_id': data['data']['run_id']})
                assert len(status.structuredContent['data']['run']['events']) == 2
                rejected = await session.call_tool('merge_to_test', {
                    'run_id': data['data']['run_id'], 'approved_by_user': False})
                assert rejected.structuredContent['data']['results'][0]['status'] == 'rejected'
                merged = await session.call_tool('merge_to_test', {
                    'run_id': data['data']['run_id'], 'approved_by_user': True})
                assert json.loads(merged.content[0].text) == merged.structuredContent
                assert merged.structuredContent['data']['results'][0]['status'] == 'merged'
                assert fixture.git(fixture.work, 'rev-parse', 'HEAD') == head


    asyncio.run(asyncio.wait_for(exercise(), timeout=20))
