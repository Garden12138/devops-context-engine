import base64
import os
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, ContentBlock, ImageContent, TextContent

from dce.errors import DceError, ErrorCode
from dce.loop.bugs import ImageBytes, get_bug, list_bugs, resolve_bugs
from dce.loop.build import poll_builds, start_builds
from dce.loop.deploy import deploy
from dce.loop.deploy import status as service_status
from dce.loop.gitops import merge_repositories
from dce.loop.plan import make_plan
from dce.loop.runs import load_run, status, update_run
from dce.output import (
    bug_output,
    check_output,
    compact,
    invoke,
    plan_output,
    scan_output,
    status_output,
    success,
)
from dce.platforms.gitlab import GitLab
from dce.platforms.http import PlatformClient
from dce.platforms.portainer import Portainer
from dce.platforms.zentao import ZenTao
from dce.settings import Settings, load_settings
from dce.workspace.config import load_config, locate_workspace
from dce.workspace.doctor import check
from dce.workspace.scan import scan


class Runtime:
    def __init__(self, connections: Path | None = None, credentials: Path | None = None,
                 workspace: Path | None = None) -> None:
        self.connections = connections or Path(os.environ.get(
            'DCE_CONNECTIONS', str(Path.home() / '.config/dce/connections.toml'),
        ))
        self.credentials = credentials or Path(os.environ.get(
            'DCE_CREDENTIALS', str(Path.home() / '.config/dce/credentials.env'),
        ))
        self.workspace = workspace or (Path(os.environ['DCE_WORKSPACE'])
                                       if os.environ.get('DCE_WORKSPACE') else None)
        self.settings: Settings | None = None

    @contextmanager
    def zentao(self) -> Iterator[ZenTao]:
        if self.settings is None:
            self.settings = load_settings(self.connections, self.credentials)
        with PlatformClient(self.settings.platform('zentao'), self.settings) as http:
            yield ZenTao(http)

    def call(self, tool: str, *, image_sink: list[ImageBytes] | None = None,
             **arguments: Any) -> dict[str, Any]:
        def operation() -> dict[str, Any]:
            ws = locate_workspace(arguments.get('workspace'), self.workspace, Path.cwd())
            if tool == 'service_status' and ((arguments.get('run_id') is None)
                                             == (arguments.get('service') is None)):
                raise DceError(ErrorCode.CONFIG_INVALID,
                               'service_status: run_id 与 service 必须且只能提供一个。',
                               '部署后按 run_id 核验，或按配置中的 service 名称查询。')
            if tool == 'dce_status':
                return status_output(status(ws, arguments.get('run_id')))
            if tool == 'run_update':
                updated = update_run(ws, load_config(ws), arguments['run_id'],
                                     arguments.get('verification'), arguments.get('record'),
                                     arguments.get('note'))
                return success(f"运行记录 {updated['run_id']} 已更新，阶段 {updated['stage']}。",
                               {'run_id': updated['run_id'], 'stage': updated['stage']})
            if tool == 'deploy_plan':
                cfg = load_config(ws)
                params = {k: v for k, v in arguments.items() if k != 'workspace'}
                with ExitStack() as stack:
                    plan = make_plan(ws, cfg, **params,
                                     bug_client=lambda: stack.enter_context(self.zentao()))
                return plan_output(plan, cfg)
            if tool == 'merge_to_test':
                return merge_repositories(
                    ws, load_config(ws), load_run(ws, arguments['run_id']),
                    arguments.get('repos'), arguments.get('approved_by_user', False))
            if tool == 'bug_resolve':
                cfg = load_config(ws)
                resolve_run = load_run(ws, arguments['run_id'])
                with self.zentao() as client:
                    results = resolve_bugs(ws, cfg, resolve_run, arguments.get('bug_ids'),
                                           arguments.get('comment'), client=client)
                count = sum(result['status'] == 'resolved' for result in results)
                return success(f'禅道已解决 {count}/{len(results)} 个缺陷。', {'results': results})
            if self.settings is None:
                self.settings = load_settings(self.connections, self.credentials)
            if tool in {'service_deploy', 'service_status'}:
                cfg = load_config(ws)
                run = load_run(ws, arguments['run_id']) if arguments.get('run_id') else None
                with PlatformClient(self.settings.platform('portainer'), self.settings) as http:
                    if tool == 'service_deploy':
                        assert run is not None
                        return deploy(ws, cfg, run, arguments.get('items'), client=Portainer(http))
                    return service_status(
                        ws, cfg, run if run is not None else arguments['service'],
                        arguments.get('wait_seconds', 30), arguments.get('logs_tail', 0),
                        client=Portainer(http))
            if tool in {'ci_build', 'ci_status'}:
                cfg, run = load_config(ws), load_run(ws, arguments['run_id'])
                with PlatformClient(self.settings.platform('gitlab'), self.settings) as http:
                    if tool == 'ci_build':
                        return start_builds(
                            ws, cfg, run, arguments.get('items'),
                            arguments.get('retry_failed', False), client=GitLab(http))
                    return poll_builds(ws, cfg, run, arguments.get('wait_seconds', 30),
                                       client=GitLab(http))
            if tool in {'bug_list', 'bug_get'}:
                cfg = load_config(ws)
                params = {k: v for k, v in arguments.items() if k != 'workspace'}
                with self.zentao() as client:
                    if tool == 'bug_list':
                        return bug_output(list_bugs(cfg, client=client, ws=ws, **params))
                    view, delivered = get_bug(cfg, client=client, ws=ws, **params)
                    if image_sink is not None:
                        image_sink.extend(delivered)
                    return bug_output(view)
            if tool == 'project_setup':
                if arguments.get('action') == 'scan':
                    return scan_output(scan(ws, self.settings))
                if arguments.get('action') == 'check':
                    return check_output(check(ws, self.settings))
                raise DceError(ErrorCode.CONFIG_INVALID,
                               'project_setup.action 必须为 scan 或 check。')
            raise DceError(ErrorCode.CONFIG_INVALID, f'未知 DCE 工具 {tool!r}。')

        return invoke(operation, lambda: self.settings.secrets() if self.settings else ())


def create_server(connections: Path | None = None, credentials: Path | None = None,
                  workspace: Path | None = None) -> FastMCP:
    runtime = Runtime(connections, credentials, workspace)
    mcp = FastMCP('DCE 2.0')

    def call(tool: str, arguments: dict[str, Any]) -> CallToolResult:
        arguments.pop('call', None)  # locals() also includes the tool closure's free variable.
        images: list[ImageBytes] = []
        payload = runtime.call(tool, image_sink=images, **arguments)
        content: list[ContentBlock] = [TextContent(type='text', text=compact(payload))]
        if payload['ok']:
            content.extend(ImageContent(type='image', data=base64.b64encode(i.content).decode(),
                                        mimeType=i.mime) for i in images)
        return CallToolResult(content=content,
                              structuredContent=payload, isError=not payload['ok'])

    @mcp.tool(description='扫描工作区生成配置草稿，或检查配置、仓库与平台连接；初始化时使用。')
    def project_setup(action: Literal['scan', 'check'], workspace: str | None = None
                      ) -> CallToolResult:
        return call('project_setup', locals())

    @mcp.tool(description='读取本地配置和运行记录，恢复闭环进度；可指定 run_id 查看详情。')
    def dce_status(run_id: str | None = None, workspace: str | None = None) -> CallToolResult:
        return call('dce_status', locals())

    @mcp.tool(description='列出配置产品的禅道缺陷；修复开始时按账号和状态筛选。')
    def bug_list(scope: Literal['mine', 'all'] = 'mine',
                 status: Literal['active', 'resolved', 'all'] = 'active', limit: int = 20,
                 workspace: str | None = None) -> CallToolResult:
        return call('bug_list', locals())

    @mcp.tool(description='读取配置产品中的缺陷正文、图片与历史；定位修复前使用。')
    def bug_get(bug_id: int, images: bool = True, max_images: int = 6,
                workspace: str | None = None) -> CallToolResult:
        return call('bug_get', locals())

    @mcp.tool(description='根据仓库改动生成部署计划和打包顺序表；自审后、合并确认前使用。')
    def deploy_plan(bug_ids: list[int], repos: list[str] | None = None,
                    feature_branches: dict[str, str] | None = None, run_id: str | None = None,
                    add_items: list[dict[str, Any]] | None = None,
                    drop_items: list[str] | None = None, workspace: str | None = None
                    ) -> CallToolResult:
        return call('deploy_plan', locals())

    @mcp.tool(description='将计划中的特性分支合入测试分支；需要用户已明确同意合并。')
    def merge_to_test(run_id: str, repos: list[str] | None = None, approved_by_user: bool = False,
                      workspace: str | None = None) -> CallToolResult:
        return call('merge_to_test', locals())

    @mcp.tool(description='触发计划内的 CI job；测试分支合并完成后使用。')
    def ci_build(run_id: str, items: list[str] | None = None, retry_failed: bool = False,
                 workspace: str | None = None) -> CallToolResult:
        return call('ci_build', locals())

    @mcp.tool(description='读取构建状态和镜像 digest；构建触发后轮询使用。')
    def ci_status(run_id: str, wait_seconds: int = 30,
                  workspace: str | None = None) -> CallToolResult:
        return call('ci_status', locals())

    @mcp.tool(description='重新拉取镜像并更新计划内的测试服务；要求对应构建已成功。')
    def service_deploy(run_id: str, items: list[str] | None = None,
                       workspace: str | None = None) -> CallToolResult:
        return call('service_deploy', locals())

    @mcp.tool(description='读取测试服务状态、运行 digest 和日志；部署后核验使用。')
    def service_status(run_id: str | None = None, service: str | None = None,
                       wait_seconds: int = 30, logs_tail: int = 0,
                       workspace: str | None = None) -> CallToolResult:
        return call('service_status', locals())

    @mcp.tool(description='保存测试结论、截图路径和修复记录提交；浏览器验证与记录完成后使用。')
    def run_update(run_id: str, verification: dict[str, Any] | None = None,
                   record: dict[str, str] | None = None, note: str | None = None,
                   workspace: str | None = None) -> CallToolResult:
        return call('run_update', locals())

    @mcp.tool(description='把运行中的缺陷标记为已解决并按配置指派；要求验证通过且修复记录已提交。')
    def bug_resolve(run_id: str, bug_ids: list[int] | None = None, comment: str | None = None,
                    workspace: str | None = None) -> CallToolResult:
        return call('bug_resolve', locals())

    return mcp
