# CLI / MCP / 未来 REST 契约

## 1. 命令约定

- `dce --help`
- `dce doctor [--mock | --live --read-only]`
- `dce init --fixture <path> [--no-ai]` / `dce init --live --read-only --scope <name>`
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

## 6. 接入示例（实现后）

Cursor `.cursor/mcp.json`（示意，不在文档阶段直接可运行）：

```json
{
  "mcpServers": {
    "dce-local": {
      "command": "uv",
      "args": ["run", "dce", "mcp", "serve", "--transport", "stdio"]
    }
  }
}
```

工作目录与 `uv` 路径需在本地实际设置；所有 Token 由本机受控进程注入。Grok Bot 连接方案依其执行器实际能力选本地 CLI 代理或内网认证 API，禁止假设外部 Bot 可以直接访问公司内网。
