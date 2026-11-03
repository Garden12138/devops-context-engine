# Cursor 桌面版接入 DCE MCP

V1 使用本机 **stdio**：Cursor 启动和关闭 DCE 子进程，没有 HTTP 地址、端口或独立常驻服务。无需先在终端挂着一个 `dce mcp serve`。
Cursor 支持项目级 `.cursor/mcp.json` 和全局 `~/.cursor/mcp.json`；本机接入使用全局配置，方便在其他业务仓库中调用。依据：[Cursor 官方 MCP 文档](https://cursor.com/docs/mcp)（2026-11-03 核对）。

## 1. 安装与数据准备

要求 Python 3.12+、uv、Cursor 桌面版。本机已经存在 `.venv`；换机器时在 DCE 仓库根目录执行：

```bash
uv sync --locked --dev
.venv/bin/dce --help
```

选择数据模式，避免混用：

| 模式 | 数据与可用能力 | 前置条件 |
|---|---|---|
| 本次实际配置：真实 Catalog 查询 | 四类本地快照查询；Bug/流水线上游查询明确拒绝 | 已授权、已采集的本地 Catalog，无需再次输入 Token |
| 合成演示 | 六工具演示，结果为 synthetic | 单独的演示 Catalog 和 fixture |
| 实时上游读取 | BugContext / Pipeline Diagnose 读取指定上游；其余四类仍读 Catalog | 受保护进程环境中的凭证、明确的 Bug/Project allowlist 与网络授权 |

本次真实数据入口为仓库下 `.local/cursor/catalog.sqlite3`，由此前验收数据库通过 SQLite backup API 创建独立副本；不覆盖原始验收库、不执行新扫描。真实库及本机路径记录不入 Git。快照采集时间以工具返回的证据为准，不能当作最新运行状态。

本机落地记录：Cursor 3.27.6，全局服务名 `dce`，已观察到 Cursor 启动 DCE 子进程；SDK stdio 检查四类查询通过。Agent 内实际调用仍待单独确认。配置备份位置和可直接使用的本机提示词见 `.local/cursor/setup.json` 与 `.local/cursor/USAGE.md`。

若没有真实 Catalog，只运行下面的合成演示，另用 `dce-demo` 配置名称：

```bash
.venv/bin/dce --catalog .local/cursor-demo/catalog.sqlite3 init \
  --fixture fixtures/synthetic-discovery.json --no-ai
```

## 2. 配置 Cursor

打开 `~/.cursor/mcp.json`，把下列 `dce` 条目合并进现有 `mcpServers`，不要覆盖其他服务。把两处 `/absolute/path/to/devops-context-engine` 换成当前机器的仓库绝对路径：

```json
{
  "mcpServers": {
    "dce": {
      "type": "stdio",
      "command": "/absolute/path/to/devops-context-engine/.venv/bin/dce",
      "args": [
        "--catalog",
        "/absolute/path/to/devops-context-engine/.local/cursor/catalog.sqlite3",
        "mcp", "serve", "--transport", "stdio", "--live", "--read-only"
      ],
      "env": {
        "DCE_AI_ENABLED": "false",
        "DCE_ALLOW_HTTP": "false"
      }
    }
  }
}
```

这里的 `--live` 用于阻止 Bug/流水线回退到默认 fixture；没有 `--zentao-bug` / `--gitlab-project` 时，它们在请求平台前返回 `PERMISSION_DENIED`。此组合不会启动实时扫描，也不需要配置上游地址或凭证。不要为了消除拒绝提示删掉 `--live`。

`command` 必须可执行，Catalog 必须已经存在且是预期数据库；DCE 本身允许创建空库，所以拼错路径可能表现为“连接成功但没数据”。使用绝对路径可以避免 Cursor 工作目录和 PATH 的差异。无需填写 `envFile`，DCE 不自动加载 `.env`。

若选择合成演示，将 Catalog 改为演示库，删除 `--live` / `--read-only`，并追加：

```json
["--fixture", "/absolute/path/to/devops-context-engine/fixtures/synthetic-discovery.json"]
```

不要给真实 Catalog 配置合成模式，否则 Bug/流水线结果会来自 fixture。

## 3. 启动、检查与使用

1. 打开 Cursor 桌面版的工作区。
2. 在设置中的 MCP 页面找到 `dce` 并启用；新版本可从 Customize 查找，其他版本可能显示 Tools & MCP。若出现新增服务器信任提示，由用户确认。
3. 确认显示六个工具。若未更新，先关闭再开启 `dce`；必要时保存工作后执行 `Developer: Reload Window`。通常不需要重启电脑。
4. 在 Agent 会话发送下面第一条提示词，检查真实宿主调用。

可直接使用的提示词：

```text
调用 dce 的 discovery_status，汇总扫描状态、待审核数量和未验证项。
只读取，不扫描、不确认映射、不构建、不部署。
```

```text
调用 dce 的 project_context；source 使用 Catalog 中的来源实例 ID，
project_key 使用该来源下的仓库 ID，depth=2。
只说明已有证据和候选关系，缺失信息保留未确认。
```

```text
调用 dce 的 service_trace，service_key 使用 Catalog 的 service 实体 ID，
direction=both，max_depth=2；说明源码、镜像和服务之间已知与缺失的证据。
```

| 工具 | 本次模式的行为 |
|---|---|
| `discovery_status` | 本地扫描记录、异常、待审核数量 |
| `project_context` | 本地项目/仓库及证据关系；source 是来源实例 ID |
| `service_trace` | 本地 service 的关联追踪 |
| `deployment_inspect` | 本地 stack/service 保存快照；不刷新 Portainer，健康可为 unknown |
| `bug_context` | 未设置上游范围，返回 PERMISSION_DENIED |
| `pipeline_diagnose` | 未设置上游范围，返回 PERMISSION_DENIED |

查找输入 ID 时，可在 DCE 仓库的本机终端运行；结果可能包含内部元数据，不要提交或公开粘贴：

```bash
.venv/bin/dce --catalog .local/cursor/catalog.sqlite3 catalog list --kind repository
.venv/bin/dce --catalog .local/cursor/catalog.sqlite3 catalog list --kind service
.venv/bin/dce --catalog .local/cursor/catalog.sqlite3 catalog list --kind stack
```

不要混用 ZenTao 项目、GitLab 仓库、Portainer Stack 的数字 ID。`candidate` 仍需人工复核；MCP 没有确认映射或任何写平台工具。

## 4. 独立检查 stdio 是否正常

在 DCE 仓库根目录执行：

```bash
.venv/bin/python scripts/check_mcp_stdio.py \
  --catalog .local/cursor/catalog.sqlite3
```

检查器从 `/` 工作目录启动实际 DCE 子进程，验证 initialize、六工具 schema、四类成功查询、两类 scope 拒绝、未知写工具拒绝、16 KB 输出预算和 Catalog 数量不变。只打印状态/计数，不打印私有工具正文或原始错误；失败退出码为 1。

检查器刻意移除继承的 `DCE_*` 配置，并使用无上游 allowlist 的只读参数；它只验证本文的 Catalog 模式。`status=passed` 证明 DCE stdio 可运行，不能代替 Cursor 界面的启用状态或一次 Agent 实际调用。

本机配置位置、数据来源、检查结果及 Host 状态保存在 gitignored 的 `.local/cursor/`。更新真实 Catalog 时先停用 Cursor 的 `dce`，对新的授权数据库使用 SQLite backup API 替换副本，再运行检查器并重新启用；不要用 fixture init 覆盖真实库，也不要在数据库使用中直接复制 SQLite/WAL 文件。

## 5. 后续启用实时 Bug / 流水线

实时模式需要一个由本机 Secret Manager/系统 Keychain 注入凭证的非交互启动环境；Cursor 的 stdio 子进程不能运行 `read` / `getpass` 交互式输入。此前验收入口中的一次性 Token 不会自动留给 Cursor。

- ZenTao：`DCE_ZENTAO_URL`、`DCE_ZENTAO_INSTANCE_ID`、`DCE_ZENTAO_TOKEN`；启动参数按授权逐项增加 `--zentao-bug <bug-id>`。
- GitLab：`DCE_GITLAB_URL`、`DCE_GITLAB_INSTANCE_ID`、`DCE_GITLAB_TOKEN`；逐项增加 `--gitlab-project <project-id>`。
- 来源实例 ID 必须与已有 Catalog 一致，不能随意换一个别名。凭证只能在受保护进程环境中提供，不写入 MCP JSON、文档或命令行参数。
- 对 HTTP 平台，必须在已有明确授权范围内才放行 `DCE_ALLOW_HTTP`；本文默认仍为 false。需要同步修改示例中的环境覆盖项，不能只在终端设置后假定生效。
- 从终端 export 不会更新已经运行的 Cursor 进程环境；需使用受控启动器或保存工作后从该环境启动 Cursor，并重新核验。本文未安装密钥管理器，也未配置凭证自动刷新。
- 禅道 Token 若为短期会话，失效会返回 AUTH_FAILED；在本机安全认证后重新注入、重启 MCP。V1 不承诺自动续期。
- `include_assets=false` 保持不读取真实图片。流水线失败时产品可能读取 trace；本轮未授权私有日志，不应直接扩大到任意失败流水线。

本次配置没有开启这两类实时上游能力。更多平台范围、附件和失败日志的真实验证继续按 [V1 验收状态](../harness/v1-acceptance-status.md) 记录。

## 6. 常见故障与停用

| 现象 | 处理 |
|---|---|
| 找不到 dce / ENOENT | 核对绝对路径，运行 `uv sync --locked --dev`；移动仓库后更新配置 |
| 连接即关闭 | 先运行独立检查；检查 Python 版本、Catalog 文件与读写权限。stdout 只能输出协议帧，启动器不能 echo |
| 已连接但无数据 / NOT_FOUND | 核对是否误创建空库，以及 source、资源种类、ID 是否匹配 |
| Bug/流水线 PERMISSION_DENIED | 本次空上游 allowlist 的预期行为；按第 5 节配置后再启用 |
| AUTH_FAILED / NETWORK_UNAVAILABLE | 仅实时模式涉及；本机安全更新凭证或检查内网，不在聊天粘贴 Token/原始日志 |
| stdio 检查通过但 Cursor 不显示 | 确认编辑的是全局文件或当前项目配置，检查同名项目级配置、启用开关及组织 MCP 策略；重载窗口 |

临时停用：在 Cursor 的 MCP 页面关闭 `dce`。卸载接入：仅删除 `mcpServers.dce` 条目，保留其他 MCP。本机配置安装前应备份；备份可能含其他服务凭证，需保留在本机并限制权限，不提交 Git。

安全规范见 [SECURITY.md](SECURITY.md)，通用安装与 CLI 运维见 [OPERATIONS.md](OPERATIONS.md)。
