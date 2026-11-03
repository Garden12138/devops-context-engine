# DevOps Context Engine (DCE)

> 面向 Cursor、Codex 和其他可调用工具的 Coding Agent 的「研发环境发现 + 可信映射 + 缺陷上下文」中间层。

**V1.0 离线实现已通过 T0–T7 验收，三平台限定只读与本轮已实现核心路径真实补验通过。Cursor 已配置并启动 MCP；尚未覆盖的外部路径与 Host 内实际工具调用单列 `not_verified`。**

验收证据见 [离线报告](harness/acceptance-report.md) 和 [执行记录](harness/build-log.md)。
离线基线为 133 项测试，含 CLI/MCP 子进程和独立 wheel 安装验证。
真实验证暴露的 HTTP 压缩响应问题已修复，该次 139 项测试通过，总体覆盖率 98.58%（行 99.19%、分支 96.66%）；见[修复回归摘要](harness/reports/http-encoding-summary.json)。
Cursor 能力检查发现的契约缺口已修复：最新 144 项测试通过，总体覆盖率 98.73%，ruff 与 strict mypy 通过；见 [MCP 契约修复摘要](harness/reports/mcp-contract-summary.json)。
已取得三平台限定只读、源码项目 live discover、真实 BugContext/成功流水线诊断与六工具处理证据，捕获数据的 Catalog/CLI 和独立 MCP stdio 集成通过；见 [V1 验收状态](harness/v1-acceptance-status.md)。业务系统自身的 Bug 修复回归不属于 DCE V1 验收。

开发环境（Python 3.12+）：`uv sync --locked --dev`。
已验证：`uv run dce --help`、`uv run dce doctor --mock`、
`uv run pytest -q --cov=src/dce --cov-report=term-missing`、`uv run ruff check .`、`uv run mypy src`。
配置使用显式 TOML 与进程环境，不自动读取 `.env`。本轮限定真实验收通过，未覆盖的范围按验收矩阵标记。

## 目标

打通 ZenTao、GitLab、Portainer（含 Docker Swarm），建立从 **业务/缺陷 → 代码仓库/模块 → CI 构建 → OCI 镜像 → 部署配置 → Stack/运行服务/环境** 的可追溯关系，向 CLI/MCP 提供精简、稳定、低 Token 的上下文。

**V1 只读发现 + 规则证据 + AI 候选 + 人工审核 + Catalog + CLI/MCP。** 自动触发构建/部署、修改禅道状态以及代码自动修复工作流是 V1.2/V2.0 规划项，不在 V1 默认实现范围。

## 从哪里开始

1. 阅读 [GOALS.md](GOALS.md)、[AGENTS.md](AGENTS.md) 和 [PLANS.md](PLANS.md)。
2. V1 的四份规范：[`requirements.md`](specs/001-dce-v1/requirements.md)、[`design.md`](specs/001-dce-v1/design.md)、[`tasks.md`](specs/001-dce-v1/tasks.md)、[`acceptance.md`](specs/001-dce-v1/acceptance.md)。
3. 核心补充文档在 `docs/`，尤其是平台适配、发现关联、数据模型和安全。
4. Codex 直接使用 [`prompts/CODEX_LONG_TASK.md`](prompts/CODEX_LONG_TASK.md)；Cursor 使用 [`prompts/CURSOR_LONG_TASK.md`](prompts/CURSOR_LONG_TASK.md)。
5. 长任务中断后按 [`prompts/RESUME.md`](prompts/RESUME.md) 恢复，不能依赖聊天上下文自行记住所有进度。

## 目录

```text
.
├── AGENTS.md                 # Codex/Cursor 共用项目规则
├── GOALS.md                  # 目标、边界、完成定义
├── PLANS.md                  # 分阶段执行与进度记录协议
├── PROMPTS.md                # 长任务提示词入口
├── specs/001-dce-v1/        # 四份正式 Spec
├── docs/                     # 架构、发现、映射、接口、安全、运维等
├── docs/github/              # GitHub 建仓说明
├── prompts/                  # Codex / Cursor / 续跑提示词
├── examples/                 # 无密钥、脱敏配置示例
├── fixtures/                 # 合成测试数据，绝无内网原始数据
├── src/dce/                  # Adapter、发现、Catalog、服务、CLI/MCP
├── tests/                    # 离线单元、安全、CLI/MCP 集成测试
├── uv.lock                   # 统一依赖锁
├── harness/                  # 分阶段记录、验收与覆盖率报告
└── .cursor/rules/            # Cursor 项目级规则
```

## 初始化和权限原则

- **不从真实平台直接开始测试写操作。** 默认 Mock/Fixture；真实 API 仅在配置 `--live --read-only` 后启用，并在用户授权范围内扫描。
- 环境文件、Token、Cookies、截图、原始日志、内部网络地址、私有仓库内容只存本地安全区域；**不得推送到公开 GitHub**。
- 保留证据、版本和环境维度；任何 AI 推测只是候选，无法仅凭相似名称自动批准。
- 真实部署目标必须校验 Portainer Endpoint/Swarm ID/Stack/Service，并独立审批；V1 不暴露部署工具。

## Cursor 桌面版接入

安装、全局配置、启动、自检、使用提示词与排错见 [Cursor MCP 接入文档](docs/CURSOR_MCP_SETUP.md)。
stdio 子进程由 Cursor 管理，无需单独运行后台服务或开放端口。真实 Catalog 查询配置（库须预先存在，路径替换为本机绝对路径）：

```json
{"mcpServers":{"dce":{"type":"stdio","command":"/absolute/path/to/repo/.venv/bin/dce","args":["--catalog","/absolute/path/to/repo/.local/cursor/catalog.sqlite3","mcp","serve","--transport","stdio","--live","--read-only"],"env":{"DCE_AI_ENABLED":"false","DCE_ALLOW_HTTP":"false"}}}}
```

服务提供六个只读工具，结果在 `structuredContent`；无审核/构建/部署工具。上述配置使四类 Catalog 查询可用；未指定上游 allowlist 的 Bug/流水线工具返回 PERMISSION_DENIED，不读取 fixture 或公司平台。合成演示与实时模式的条件见接入文档。
附件为当前会话授权的 `dce://assets/…` 资源，不暴露上游 URL。
Grok Bot 的具体 MCP 支持与真实内网接入均为 `not_verified`，需在用户执行器实测。

本机已完成 Cursor 配置安装并观察到由 Cursor 启动的 DCE 进程；标准 SDK stdio 自检通过。Cursor Agent 实际调用仍单独记录，见 [接入检查摘要](harness/reports/cursor-mcp-summary.json)。

契约 revision 1.1 已在工具描述中声明平台、数据源和会话状态，并为每个返回数据发布完整 Schema；无需翻查服务端代码判断能力。`ready` 不代表上游认证成功，`snapshot_at` 是响应时间；刷新 MCP 后可在新会话按接入文档重新做仅枚举检查。

## 状态

- [x] V1 设计规格与可复现的脱敏测试数据
- [x] V1 代码实现、单元测试和离线验收
- [x] 三平台限定元数据真实只读 smoke 与捕获数据 Catalog/CLI 验证（凭证仅进程内使用）
- [x] 限定源码项目 live discover 与六个既有 MCP 工具处理的真实补验
- [ ] 更多真实平台范围/版本及受本轮安全边界排除的路径验证（分别记录 not_verified）
- [ ] V1.1 MCP + BugContext 的实际 Agent 验收

## 开发建议

Python 3.12+ / Typer / Rich / httpx / Pydantic / SQLAlchemy + SQLite / MCP Python SDK；后续内网共享服务可用 FastAPI。采用可替换的 AI Provider，默认 AI 关闭也能发现资源、提出规则关联并允许审核。

> 本文件与项目所有示例均避免保留公司私网信息。任何新建公开仓库前请阅读 `docs/github/REPOSITORY_SETUP.md`。
