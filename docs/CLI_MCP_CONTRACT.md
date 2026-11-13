# CLI / MCP / 未来 REST 契约

## 1. 命令约定

- `dce --help`
- `dce doctor [--mock | --live --read-only]`
- `dce init --fixture <path> [--no-ai]` / `dce init --live --read-only --scope '<ScanScope JSON>'`
- `dce discover --zentao-project <id>`、`--gitlab-group <group>`、`--gitlab-project <id>`、`--portainer-stack <id>`、`--portainer-endpoint <id>`；可组合。
- `dce catalog list [--kind <type>] [--format json|table]`
- `dce catalog anomalies [--format json|table]`
- `dce trace service <key> --direction both --max-depth 5`
- `dce mapping suggest [--no-ai]`、`dce mapping review`、`dce mapping verify`
- `dce bug context <id> [--format json|table]`
- `dce pipeline diagnose <project> <pipeline_id>`
- `dce stack inspect <stack_id>`
- `dce mcp serve --transport stdio`

所有 CLI 默认只读公司平台。`init`/`mapping review` 只会写本地 Catalog 和审核日志；写本地不等于有权限写远端系统。真实 `--live` 与 `--read-only` 显式配对。

## 2. 输出 JSON 统一结构

```json
{
  "schema_version": "1.0",
  "request_id": "req-demo-001",
  "status": "ok",
  "data": {},
  "evidence": [],
  "warnings": [],
  "uncertainties": [],
  "truncated": false,
  "omissions": [],
  "next_action": null,
  "snapshot_at": "2026-10-31T00:00:00Z"
}
```

错误统一：`{ "status": "error", "error": { "code": "PERMISSION_DENIED", "message": "...", "retryable": false } }`，不返回原始 header / URL 中的 Token。

## 3. MCP 工具清单（V1）

| Tool | 输入 | 返回 | 写权限 |
|---|---|---|---|
| `bug_context` | `bug_id`, `include_assets` | Bug 摘要、候选项目/模块、evidence、asset refs | 无 |
| `project_context` | `source`, `project_key`, `depth` | Project/Repo/Module/Build/Deploy 关系 | 无 |
| `service_trace` | `service_key`, `direction`, `max_depth` | Image/CI/Module/Environment 追踪 | 无 |
| `pipeline_diagnose` | `project_key`, `pipeline_id` | Job、失败阶段、有限日志摘要 | 无 |
| `deployment_inspect` | `stack_key` 或 `service_key` | Catalog 保存的 Stack/Swarm 快照与关系；不刷新或实时对比，健康 `unknown` | 无 |
| `discovery_status` | `scan_id?` | 扫描进度、异常和待审核数量 | 无 |

MCP 绝不暴露 `mapping_approve`, `deploy_execute`, `trigger_pipeline`, `bug_resolve` 等写工具。工具输入是受控资源 ID，不接受任意 HTTP 地址或系统命令。

## 4. 截图策略

`bug_context` 返回 `assets: [{asset_id, mime, width, height, local_path?}]`。本地 CLI 返回可访问路径；MCP 若需要图片，则使用独立权限检查后按大小上限提供 MCP Image Content 或受控 Resource。不得直接把公司内网附件 URL 随意转发给云端 Agent。

## 5. 最小化上下文

- 默认仅返回引用关系 1～2 跳、最多 20 组 Edge，提供 `cursor`/`more_available` 继续查询。
- 扫描原始配置、脚本、数据库变量值不直接进入 LLM 上下文。
- Pipeline Logs 默认只提取最后 100 行与错误关键上下文，敏感字段经脱敏处理；工具可分次拉取。

## 6. 已实现的 stdio 接入

### 自描述契约 revision 1.1（2026-11-03）

保持六个既有工具及只读边界，不新增发现、刷新、认证、审批或部署工具。`tools/list` 不发出平台请求；每个描述必须声明平台归属、Catalog/合成/实时数据源和当前会话的读取条件。scope/配置/HTTP 放行只代表配置条件，不能证明凭证有效、网络可达或接口已验证；不返回凭证、上游地址或授权 ID。

每个输入字段提供语义、默认值与限制，`deployment_inspect` 的 JSON Schema 和运行时均要求恰好一个非空资源键。每个工具发布独立的结构化 `data` Schema，信封完整声明 schema_version/request_id/status/data/evidence/warnings/uncertainties/truncated/omissions/next_action/snapshot_at，以及错误的 code/error_code/message/retryable。成功、错误及预算截断均须匹配 Schema；data=null 只允许错误或明确截断。

`snapshot_at` 为兼容保留的响应生成时间，不是平台采集时间；实体/关系的 last_verified、扫描 finished_at 和部署快照 observed_at 才说明相应证据的时间。deployment_inspect 补充已有快照 observed_at，不请求 Portainer，不将固定 unknown/unresolved/not_verified 解释为实时诊断。

验证：直接读取 tools/list 的 Schema 做 JSON Schema 校验；覆盖六工具成功/错误/截断、字段类型缺失、二选一输入、动态会话状态和无出网/凭证泄露；再跑真实 stdio SDK 和现有完整回归。标准依据：[MCP Tools / Output Schema](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)。

`tools/list` 为每个工具返回 `_meta.dce`，包括 contract_revision、data_source、availability、blockers；上游工具另有 platform。不包含 Token、URL 或 allowlist ID。描述中同步显示这些会话条件，宿主不转发 `_meta` 时也能理解限制。

| 状态 | 含义 |
|---|---|
| `local_catalog` | 只查询已保存的 Catalog；来源可以是真实采集或合成导入，本状态不验证数据来源/新鲜度 |
| `synthetic` | Bug/流水线读取 fixture，不访问真实平台 |
| `blocked` | live 模式存在空 allowlist、缺少平台配置或未放行 HTTP；blockers 列明原因 |
| `configured_not_verified` | scope/配置/传输条件已具备；不代表凭证有效、网络通畅或平台调用已经成功 |

这些状态通过启动配置计算，不通过登录、平台探测或业务工具调用获得。`openWorldHint` 仅对满足配置条件的上游工具为 true；四类本地读取为 false。`mcp_auth` 若由宿主注入，不属于 DCE 注册的六工具。传输 ready 与以上状态分别理解。

模块映射审核、规则发现、三平台 Adapter 等既有 CLI 能力不等于都已作为 MCP 工具提供。Portainer Adapter/扫描已存在；MCP 的 deployment_inspect 只读保存快照，不能实时刷新或验证健康/部署版本。Pipeline 诊断保留规则局限，不保证所有失败都能自动定位根因。写平台、触发构建、部署、回滚和禅道回写不在 V1 MCP 能力内。

结果同时在 `structuredContent` 和序列化 JSON 的 `content[type=text]`，两者语义相同；只消费文本的 Host 也能读取事实、错误码和截断标志。固定的 `DCE result.` 不能满足 Host 事实消费要求。依据 [MCP Structured Content](https://modelcontextprotocol.io/specification/2025-11-25/server/tools#structured-content)。

`output_budget` 限制两份 JSON 与转义开销合计的紧凑 UTF-8 ToolResult body，不含外层 JSON-RPC framing。同一预算下大 Catalog 响应可能更早明确截断；需要完整大结果时显式提高预算（上限 64000）或缩小查询，而非忽略遗漏。可选 `image_output_budget`（1024–3000000 字节，默认 null）只在显式配置后为原生图片设置独立的总结果上限；图片元数据的两份 JSON 仍受 output_budget 限制。原图 Reader 上限仍为 2MB，不缩图、不落盘；超限返回 not_delivered/truncated。
默认 fixture；启动时显式 `--live --read-only`，Bug/流水线上游读取还需 `--zentao-bug`/`--gitlab-project` allowlist。
资源仅当前会话授权，读取重新校验 SHA256、路径与大小。

Cursor 使用虚拟环境入口和 Catalog 的绝对路径，避免宿主 PATH / 工作目录差异；完整配置及独立 stdio 自检见 [Cursor 桌面版接入](CURSOR_MCP_SETUP.md)。
真实 Catalog 模式使用 `--live --read-only` 且上游 allowlist 为空：四类本地读取可用，Bug/流水线读取在发出请求前明确拒绝；默认 fixture 模式只适合独立的合成演示库。
所有 Token 由本机受控进程注入，不写 MCP JSON。Grok Bot 连接方案依其执行器实际能力选本地 CLI 代理或内网认证 API，禁止假设外部 Bot 可以直接访问公司内网。

## Agent-led revision 2.0

原六工具 revision 1.1 保持兼容，Catalog 关系明确为历史线索；新增三个事实查询工具，详见 [九工具清单](MCP_FACT_TOOLS.md) 与 [Host 工作流](AGENT_LED_WORKFLOW.md)。事实查询按显式 instance 与启动范围授权，不读写全局关系或项目文件。图片通过 zentao_query(image) 原生 ImageContent 交付；旧 bug_context Resource 保留。初始化/审核/refresh 在 Host 当前业务工作区完成。
