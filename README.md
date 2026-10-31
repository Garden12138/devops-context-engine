# DevOps Context Engine (DCE)

> 面向 Cursor、Codex 和其他可调用工具的 Coding Agent 的「研发环境发现 + 可信映射 + 缺陷上下文」中间层。

**V1.0 正在实施：T0–T4 可运行并通过离线测试，T5–T7 尚未验收。**

开发环境（Python 3.12+）：`uv sync --locked --dev`。
已验证：`uv run dce --help`、`uv run dce doctor --mock`、
`uv run pytest -q --cov=src/dce --cov-report=term-missing`、`uv run ruff check .`、`uv run mypy src`。
配置使用显式 TOML 与进程环境，不自动读取 `.env`。真实平台 smoke 尚未验证。

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
├── harness/                  # 长任务执行记录位置（初始模板）
└── .cursor/rules/            # Cursor 项目级规则
```

## 初始化和权限原则

- **不从真实平台直接开始测试写操作。** 默认 Mock/Fixture；真实 API 仅在配置 `--live --read-only` 后启用，并在用户授权范围内扫描。
- 环境文件、Token、Cookies、截图、原始日志、内部网络地址、私有仓库内容只存本地安全区域；**不得推送到公开 GitHub**。
- 保留证据、版本和环境维度；任何 AI 推测只是候选，无法仅凭相似名称自动批准。
- 真实部署目标必须校验 Portainer Endpoint/Swarm ID/Stack/Service，并独立审批；V1 不暴露部署工具。

## 状态

- [x] V1 设计规格与可复现的脱敏测试数据
- [ ] V1 代码实现、单元测试和离线验收（交给 Codex/Cursor 完成）
- [ ] V1 真实内网只读 smoke 测试（凭证只保存在本地）
- [ ] V1.1 MCP + BugContext 的实际 Agent 验收

## 开发建议

Python 3.12+ / Typer / Rich / httpx / Pydantic / SQLAlchemy + SQLite / MCP Python SDK；后续内网共享服务可用 FastAPI。采用可替换的 AI Provider，默认 AI 关闭也能发现资源、提出规则关联并允许审核。

> 本文件与项目所有示例均避免保留公司私网信息。任何新建公开仓库前请阅读 `docs/github/REPOSITORY_SETUP.md`。
