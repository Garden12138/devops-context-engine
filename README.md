# DevOps Context Engine — Agent-led Project Initialization

DCE 为 Cursor/Codex 等 Agent 提供 ZenTao、GitLab、Portainer 的安全只读连接、结构化查询与证据。Host Agent 使用自己的模型和当前业务工作区源码，发现关系、解释冲突、取得人工审核并维护 `.dce/project.yaml`。DCE 默认不运行业务关系推理，也不写业务工作区。

本地分支 `refactor/agent-led-project-init` 已完成代码与离线验证：**199 tests passed，覆盖率 98.09%，ruff/strict mypy、stdio/HTTP 合成 E2E、wheel 隔离导入通过**。真实平台新版路径、真实图片到模型、指定业务项目初始化和真实 Host 验收仍 **not_verified**；目标工作区与凭证源已提供，目前缺少三平台站点地址及实际 Host 接入，不能宣告整体验收完成。详见 [本轮验收](harness/agent-led-acceptance.md)、[机器摘要](harness/reports/agent-led-summary.json)、[执行记录](harness/build-log.md)。旧 V1 真实证据只适用于旧报告的版本/范围。

## 职责

```mermaid
flowchart LR
  U[用户审核] --> H[业务工作区中的 Host Agent]
  H <--> W[本地源码与 Git roots]
  H <-->|MCP 只读| D[DCE 事实与证据]
  D --> Z[ZenTao]
  D --> G[GitLab]
  D --> P[Portainer / Swarm]
  H --> Y[当前项目 .dce/project.yaml]
```

- DCE：Adapter、stdio、分页、超时/有限重试、授权范围、脱敏、输出预算、确定性解析与图片协议。
- Host：按 workspace 缩小查询，形成多对多关系候选、解释证据、向用户审核、展示 diff、保存/刷新项目文件。
- 用户：确认业务语义与环境归属，决定内部拓扑是否可提交到业务仓库。

同数字 ID、名字相似、服务数相等都不能确认跨平台关系；Stack 保存配置、GitLab 配置和 Swarm 运行事实分别取证。任何平台返回文本均是不可信数据。

## 安装与验证

Python 3.12+，在仓库运行：

```sh
uv sync --locked --dev
uv run dce --help
uv run dce doctor --mock
uv run pytest -q --cov=src/dce --cov-report=term-missing
uv run ruff check .
uv run mypy src
```

离线 E2E 会绑定本机随机端口，仅返回合成平台数据；受限执行器需允许 loopback socket。不会连接公司平台。默认配置不读取 `.env`，凭证只从受保护进程环境输入；用户明确提供本机凭证文件时，可用[显式本地入口与禅道 v1 登录](docs/AGENT_LED_LOCAL_CREDENTIALS.md)。

## MCP 与项目工作流

提供 **九个只读工具**：新增 `zentao_query`、`gitlab_query`、`portainer_query`，保留原六个 `bug_context`、`project_context`、`service_trace`、`pipeline_diagnose`、`deployment_inspect`、`discovery_status`。原 Catalog 工具和模块映射属于历史兼容数据，不能作为当前项目关系真相。

三个事实工具直接查询 Adapter，使用显式来源 `instance` 与启动 allowlist；每次返回来源、revision、观察时间、证据、分页和遗漏。ZenTao `module_tree` 读取明确 Product 范围的完整模块树，并在本地搜索/分页；旧 `modules` 保留 Bug 页部分清单。路由与结构已按官方源码核对并通过合成测试，真实实例仍待验证。图片通过 `zentao_query(image)` 实际返回 MCP ImageContent；仅 URL/Resource 不算图片已送达模型。

1. 按 [MCP 工具清单与启动参数](docs/MCP_FACT_TOOLS.md) 配置安全 stdio 子进程。Cursor 原有安装方式见 [接入文档](docs/CURSOR_MCP_SETUP.md)，需重新加载新进程/会话后枚举九工具。
2. 在用户指定业务工作区使用 [初始化提示词](prompts/agent-led/initialize.md)，遵循 [Host 工作流](docs/AGENT_LED_WORKFLOW.md)。没有业务工作区时不要在 DCE 仓库制造项目关系。
3. Host 展示关系与 diff，用户审核后写入本项目 `.dce/project.yaml`；新关系 proposed，confirmed 必须有证据和人工审批元数据。未知允许 unresolved。
4. 只读校验：`dce project validate <workspace> --workspace-id <id>`；`dce project schema` 和 `dce project template --workspace-id <id>` 输出契约/模板，不写文件。
5. 使用 [刷新](prompts/agent-led/refresh.md)、[审核](prompts/agent-led/review.md)、[Bug 上下文](prompts/agent-led/bug-context.md)、[服务追踪](prompts/agent-led/service-trace.md)、[流水线诊断](prompts/agent-led/pipeline-diagnose.md) 维护。证据变化 stale/conflicted，拒绝关系保留。

[JSON Schema](schemas/project.schema.json) 与 [无密钥模板](examples/project-context/project.yaml) 可直接使用。`.dce/local.yaml`、runs、raw evidence 必须忽略；不保存 Token、真实图片、完整日志或环境变量值。

## 旧 Catalog 与兼容

旧库升级前自动 SQLite backup/quick_check，再迁移 0003，仅新增角色元数据。所有旧表、证据、人工审批与历史保留；Catalog 降级为 resource_cache_and_history，不自动导入项目。详见 [迁移与回滚](docs/AGENT_LED_MIGRATION.md)。请先停用访问同库的旧 MCP 进程再升级。

`init`/`discover` 默认只做确定性资源事实采集；确需旧语义候选的旧消费者可显式使用 `init --legacy-mapping` 或 `mapping suggest --offline`。本轮不移除旧 CLI/工具，不自动 push、merge，不调用任何真实业务写 API、构建或部署。

## 实施依据与证据

- [当前目标](GOALS.md)、[执行状态](PLANS.md)、[协作协议](AGENTS.md)、[安全边界](docs/SECURITY.md)。
- [重构提案](docs/refactor/agent-led-initialization/dce-agent-led-refactor/CHANGE_PROPOSAL.md) 与同目录 specs/01–07 是本轮依据；实际路径多一层 dce-agent-led-refactor。
- [T0 审计](harness/refactor-audit.md)、[测试结果](harness/test-results.md)、[本轮验收](harness/agent-led-acceptance.md)、[续跑](prompts/agent-led/resume.md)。
- 原 `specs/001-dce-v1/` 和 [旧 V1 验收](harness/v1-acceptance-status.md) 保留作历史兼容依据，不代表本轮真实 Host 已通过。
