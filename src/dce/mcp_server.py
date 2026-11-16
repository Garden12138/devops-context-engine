import os
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

from dce.errors import DceError, ErrorCode
from dce.loop.runs import status
from dce.output import check_output, compact, invoke, scan_output, success
from dce.settings import Settings, load_settings
from dce.workspace.config import locate_workspace
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

    def call(self, tool: str, **arguments: Any) -> dict[str, Any]:
        def operation() -> dict[str, Any]:
            if tool not in {'project_setup', 'dce_status'}:
                raise DceError(ErrorCode.NOT_IMPLEMENTED, f'{tool} 将在后续里程碑实现。',
                               '按 docs/v2/05-实施计划.md 的顺序完成后续里程碑。')
            ws = locate_workspace(arguments.get('workspace'), self.workspace, Path.cwd())
            if tool == 'dce_status':
                data = status(ws, arguments.get('run_id'))
                return success(f"{data['config']['name']}：{len(data['runs'])} 个运行记录。", data)
            if self.settings is None:
                self.settings = load_settings(self.connections, self.credentials)
            if arguments['action'] == 'scan':
                return scan_output(scan(ws, self.settings))
            if arguments['action'] == 'check':
                return check_output(check(ws, self.settings))
            raise DceError(ErrorCode.CONFIG_INVALID, 'project_setup.action 必须为 scan 或 check。')

        return invoke(operation, lambda: self.settings.secrets() if self.settings else ())


def create_server(connections: Path | None = None, credentials: Path | None = None,
                  workspace: Path | None = None) -> FastMCP:
    runtime = Runtime(connections, credentials, workspace)
    mcp = FastMCP('DCE 2.0')

    def call(tool: str, arguments: dict[str, Any]) -> CallToolResult:
        payload = runtime.call(tool, **arguments)
        return CallToolResult(content=[TextContent(type='text', text=compact(payload))],
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

    @mcp.tool(description='把运行中的缺陷标记为已解决并指派回提测人；要求验证通过且修复记录已提交。')
    def bug_resolve(run_id: str, bug_ids: list[int] | None = None, comment: str | None = None,
                    workspace: str | None = None) -> CallToolResult:
        return call('bug_resolve', locals())

    return mcp
