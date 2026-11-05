> 当前 Agent-led 版本保留原六工具，新增 zentao_query/gitlab_query/portainer_query，共九工具。新启动范围、instance/分页/图片说明见 [工具清单](MCP_FACT_TOOLS.md)，项目流程见 [Host 工作流](AGENT_LED_WORKFLOW.md)。本页既有配置属于 Catalog 历史接入，不会自动配置新平台范围；需停止旧连接并启动新进程/会话。旧进程/SDK 证据不代表本轮真实 Host 已通过。

2026-11-04 接续：当前机器的全局 `dce` 已备份后替换为 [显式本地凭证启动器](AGENT_LED_LOCAL_CREDENTIALS.md)，采用用户给定的 HTTP/凭证源和限定范围；其他四个 MCP 条目保持不变，配置无密码/Token。标准 SDK 对同一入口已成功读取三平台；Cursor 桌面 Agent 仍需在新会话实际枚举九工具、执行至少三次读取并完成项目初始化对话。CLI 未登录且未枚举到该条目，不能代替桌面验收。私有提示词位置随本轮执行记录保留，平台值不放入本页。

后续真实反馈：用户已确认 Cursor 中九个 DCE 工具和三次实际成功调用，额外 mcp_auth 属于宿主；初始化对话也已回传。由于该 Host 没有转发 structuredContent，旧文本 DCE result. 让模型无法看到事实/截断。服务器现同时提供相同 JSON 文本信封；关闭再开启 dce 连接，并在新会话复验文本 JSON。授权含图 Bug 的范围与显式图片预算也已装入连接，SDK 原生图片交付通过；模型实际接收仍需在 Cursor 观察。无需重复全部三平台调用或重新提供 Token。

最新复验已回传：Cursor 实际看见 JSON 文本信封，Bug 查询信封/data.truncated 均 false、data.evidence 有记录；原生 PNG ImageContent 也已进入模型可见内容，未截断、未保存或转录图片。完整项目文件已获批准，由 Host 保存并通过 CLI 校验/复读，仍为 22 proposed/1 unresolved/0 confirmed；按用户要求未暂存、未提交。此前的待复验和待保存是历史状态，不需再次执行。

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
| 当前 Agent-led：限定实时事实 | 三个事实工具 + 原六工具兼容；当前项目关系由 Host 维护 | [新范围/参数](MCP_FACT_TOOLS.md)、[显式本地入口](AGENT_LED_LOCAL_CREDENTIALS.md)、受保护凭证源 |
| 旧 V1 配置：真实 Catalog 查询 | 四类本地快照查询；Bug/流水线上游查询明确拒绝 | 已授权、已采集的本地 Catalog，无需再次输入 Token |
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
2. 在 Cursor 侧边栏打开 **Customize → MCPs**，找到名为 `dce` 的服务；其他版本可能在设置的 MCP 或 Tools & MCP 页面。若出现新增服务器信任提示，由用户确认。
3. 当前 Agent-led 版本应显示九个 DCE 工具。“重新启动 dce 连接”指把该服务旁边的开关关闭，再打开，等待工具列表重新出现。Cursor 随之启动新版本地 DCE 进程；不需要删除配置。此操作见 [Cursor 官方故障排查](https://cursor.com/help/customization/mcp#how-do-i-troubleshoot-mcp-servers)。必要时保存工作后执行 `Developer: Reload Window`。
4. 在 Agent 会话发送下面第一条提示词，检查真实宿主调用。

工具契约修正后需要重新加载 MCP，已运行的 Python 子进程不会自动导入磁盘上的新代码。若旧聊天仍显示模板化描述，重启 `dce` 后再开一个 Agent 会话执行能力检查。
同机多个 Cursor 窗口可能保留不同的 MCP 连接；观察到一个新进程不能证明其他窗口已刷新。应在实际使用的窗口关闭再开启 `dce`，再在新会话检查 revision 1.1。



### 只检查能力，不查询业务数据

```text
先读取 DCE 的 tools/list，仅依据实际 description、inputSchema、outputSchema
以及 _meta.dce（若宿主提供），列出六工具的平台、输入输出、数据源与当前会话状态。
区分 blocked、configured_not_verified、local_catalog 和 synthetic。
不要按名称推测，不读取仓库实现，不调用业务工具，不把 ready 当作平台认证成功。
若看到 mcp_auth，注明它由宿主注入，不算 DCE 工具。
```

契约 revision 1.1 的描述会直接说明 ZenTao/GitLab/Portainer 及本地/实时来源；每个 data 有独立 Schema，错误和预算截断另有约束。当前快照配置下，四个工具为 `local_catalog`，Bug/流水线为 `blocked`。完整状态定义见 [MCP 契约](CLI_MCP_CONTRACT.md)。

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

检查器还要求 `_meta.dce.contract_revision=1.1`，校验已发布的输入/输出 JSON Schema，并用返回的 Schema 验证真实查询和拒绝响应。它验证新启动子进程的契约，不能据此推定已有 Cursor 会话缓存已更新。

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

旧 V1 配置没有开启这两类实时上游能力。当前 Agent-led 实时读取和外部缺口按 [本轮验收](../harness/agent-led-acceptance.md) 记录；旧历史范围见 [V1 验收状态](../harness/v1-acceptance-status.md)。

`ready` 只表示 MCP 连接已就绪；实时读取条件以工具自身描述的 availability/blockers 为准。即使显示 `configured_not_verified`，也要经过授权的只读成功调用才能证明目标平台读取可用。

## 6. 常见故障与停用

| 现象 | 处理 |
|---|---|
| 找不到 dce / ENOENT | 核对绝对路径，运行 `uv sync --locked --dev`；移动仓库后更新配置 |
| 连接即关闭 | 先运行独立检查；检查 Python 版本、Catalog 文件与读写权限。stdout 只能输出协议帧，启动器不能 echo |
| 已连接但无数据 / NOT_FOUND | 核对是否误创建空库，以及 source、资源种类、ID 是否匹配 |
| Bug/流水线 PERMISSION_DENIED | 本次空上游 allowlist 的预期行为；按第 5 节配置后再启用 |
| AUTH_FAILED / NETWORK_UNAVAILABLE | 仅实时模式涉及；本机安全更新凭证或检查内网，不在聊天粘贴 Token/原始日志 |
| stdio 检查通过但 Cursor 不显示 | 确认编辑的是全局文件或当前项目配置，检查同名项目级配置、启用开关及组织 MCP 策略；重载窗口 |
| 描述仍是 `Read-only <name>` | Cursor 正在用旧子进程或旧聊天缓存；重启 `dce` 后在新 Agent 会话重新枚举工具 |

临时停用：在 Cursor 的 MCP 页面关闭 `dce`。卸载接入：仅删除 `mcpServers.dce` 条目，保留其他 MCP。本机配置安装前应备份；备份可能含其他服务凭证，需保留在本机并限制权限，不提交 Git。

安全规范见 [SECURITY.md](SECURITY.md)，通用安装与 CLI 运维见 [OPERATIONS.md](OPERATIONS.md)。

## 7. 项目文件与保存确认

复验提示词只是交给 Cursor Agent 的操作说明，不是审批对象。`project.proposed.yaml` 是完整项目关系草案，`project.proposed.diff` 是将它新增到业务目录的变更预览；两者保存在 DCE 的私有运行目录。最终文件为业务项目中的 `.dce/project.yaml`，供后续 Agent 初始化、刷新和定位问题时读取。

本轮草案记录 20 个 Git roots、三平台资源 ID，以及 23 条带来源/时间/证据的关系：18 条本地模块结构、1 条精确 Git remote 身份、3 条 Stack/Swarm 候选、1 条 Bug 与当前代码的未知关联。状态为 22 proposed、1 unresolved、0 confirmed，不含 Token 或密码。保存草案后仍保留这些状态，不替用户确认业务关系。

需要批准的是“允许在指定业务项目新增该文件”。用户要求严格遵循的 [规格 05 阶段 F](refactor/agent-led-initialization/dce-agent-led-refactor/specs/05-agent-workflow.md) 明确规定：“用户确认后创建/更新 `.dce/project.yaml`；写入前展示 diff”。未来逐条确认业务关系还需证据和真实审批元数据；本次文件保存审批不填写这些字段。聊天中省略关系的片段不能代替完整草案。
# V1.1 日志增量

包升级为 1.1.0 后，保留已有连接与凭证注入，仅对已批准测试环境追加 `--portainer-log-scope ENDPOINT_ID:STACK_ID`（且已有对应 `--portainer-endpoint`、`--portainer-stack`）。重载 DCE MCP，检查九工具仍在、portainer_query 契约 2.2。完整参数、有限窗口示例与权限限制见 [Scoped Service Logs](SCOPED_SERVICE_LOGS.md)；配置状态不是权限验收，当前真实日志 `not_verified`。不自动改业务 project.yaml。
