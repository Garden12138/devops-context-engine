import asyncio
import json
import os
from pathlib import Path

import yaml
from gitfixture import GitFixture
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from test_config import write_config

TOOLS = {
    'project_setup', 'dce_status', 'bug_list', 'bug_get', 'deploy_plan', 'merge_to_test',
    'ci_build', 'ci_status', 'service_deploy', 'service_status', 'run_update', 'bug_resolve',
}
PENDING = {
    'merge_to_test': {'run_id': 'demo-run', 'approved_by_user': True},
    'ci_build': {'run_id': 'demo-run'}, 'ci_status': {'run_id': 'demo-run'},
    'service_deploy': {'run_id': 'demo-run'}, 'service_status': {'service': 'demo_test_demo-web'},
    'run_update': {'run_id': 'demo-run', 'note': 'demo'}, 'bug_resolve': {'run_id': 'demo-run'},
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
                mismatch = await session.call_tool(
                    'dce_status', {'workspace': str(tmp_path.parent)},
                )
                assert mismatch.structuredContent['error']['code'] == 'WORKSPACE_MISMATCH'
                for name, arguments in PENDING.items():
                    pending = await session.call_tool(name, arguments)
                    assert json.loads(pending.content[0].text) == pending.structuredContent
                    assert pending.structuredContent['error']['code'] == 'NOT_IMPLEMENTED'

    asyncio.run(asyncio.wait_for(exercise(), timeout=20))


def test_stdio_deploy_plan_with_local_bare_origin_only(tmp_path):
    fixture = GitFixture(tmp_path / 'demo-fixture')
    cfg = yaml.safe_load(Path('examples/dce.example.yaml').read_text())
    repo = next(r for r in cfg['repos'] if r['name'] == 'demo-web')
    repo['path'] = 'demo-fixture/demo-work'
    cfg['repos'] = [repo]
    write_config(tmp_path, cfg)
    fixture.commit('src/demo.js', 'demo fix', 'fix: demo bug#4336')
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

    asyncio.run(asyncio.wait_for(exercise(), timeout=20))
