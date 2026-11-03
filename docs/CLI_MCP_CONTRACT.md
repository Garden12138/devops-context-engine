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
| `deployment_inspect` | `stack_key` 或 `service_key` | 保存配置与当前 Swarm 对比，健康 `unknown` 可见 | 无 |
| `discovery_status` | `scan_id?` | 扫描进度、异常和待审核数量 | 无 |

MCP 绝不暴露 `mapping_approve`, `deploy_execute`, `trigger_pipeline`, `bug_resolve` 等写工具。工具输入是受控资源 ID，不接受任意 HTTP 地址或系统命令。

## 4. 截图策略

`bug_context` 返回 `assets: [{asset_id, mime, width, height, local_path?}]`。本地 CLI 返回可访问路径；MCP 若需要图片，则使用独立权限检查后按大小上限提供 MCP Image Content 或受控 Resource。不得直接把公司内网附件 URL 随意转发给云端 Agent。

## 5. 最小化上下文

- 默认仅返回引用关系 1～2 跳、最多 20 组 Edge，提供 `cursor`/`more_available` 继续查询。
- 扫描原始配置、脚本、数据库变量值不直接进入 LLM 上下文。
- Pipeline Logs 默认只提取最后 100 行与错误关键上下文，敏感字段经脱敏处理；工具可分次拉取。

## 6. 已实现的 stdio 接入

结果在 `structuredContent`，文本部分只给极简状态，避免重复 JSON 消耗预算。
默认 fixture；启动时显式 `--live --read-only`，Bug/流水线上游读取还需 `--zentao-bug`/`--gitlab-project` allowlist。
资源仅当前会话授权，读取重新校验 SHA256、路径与大小。

Cursor 使用虚拟环境入口和 Catalog 的绝对路径，避免宿主 PATH / 工作目录差异；完整配置及独立 stdio 自检见 [Cursor 桌面版接入](CURSOR_MCP_SETUP.md)。
真实 Catalog 模式使用 `--live --read-only` 且上游 allowlist 为空：四类本地读取可用，Bug/流水线读取在发出请求前明确拒绝；默认 fixture 模式只适合独立的合成演示库。
所有 Token 由本机受控进程注入，不写 MCP JSON。Grok Bot 连接方案依其执行器实际能力选本地 CLI 代理或内网认证 API，禁止假设外部 Bot 可以直接访问公司内网。
