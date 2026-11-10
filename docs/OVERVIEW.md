> 历史 V1 兼容文档。当前业务关系推理与 project.yaml 归 Host，默认 DCE 核心不调用语义 Mapping；参见 [Agent-led 工作流](AGENT_LED_WORKFLOW.md)。旧实现保留作缓存/历史兼容。

# DCE V1.0 — 给项目负责人看的方案总览

## 解决的问题

**不是**新做一个禅道/GitLab/Portainer 管理台。DCE 作为 AI Coding Agent 的可靠研发上下文层，让 Agent 直接通过 API/CLI/MCP 获取缺陷、代码结构、CI 和部署信息，替代浏览器反复点击。

真实痛点有四个：

1. Bug 的复现说明常含 HTML 和截图，`files=[]` 并不代表没有图片。
2. GitLab 业务仓库可能含多个模块，独立部署仓库管理 Compose；不能“禅道项目 ↔ 一个业务仓库 ↔ 一个 Stack”硬映射。
3. 同一 Docker Image 可能运行多个 Service，且环境差异影响部署目标。
4. Portainer 旧 Stack 记录可能仍显示活动，但 `SwarmId` 已不匹配当前集群，不能作为实际部署目标。

## 最终工作方式

```text
Cursor / Codex / Grok Bot
      ↓ MCP / CLI
DevOps Context Engine
      ├── 自动发现（ZenTao / GitLab / Portainer）
      ├── 关联引擎（证据规则 + 可选 AI + 人工审核）
      ├── Service Catalog（关联、版本、快照、差异、审计）
      └── Bug Context（缺陷、截图、候选代码、构建和部署服务）
```

## 技术策略

- 规则先发现：ZenTao API、GitLab Repository Tree/CI、Compose、Swarm Service 只读 API。
- AI 后推断：只补足业务功能到代码模块的语义缺口；不能直接批准。
- 人工审核：审核一次，多个 AI Agent 反复复用已确认结果；变化时增量复核。
- 安全边界：V1 无外部写功能；构建/部署/禅道状态更新等在后续版本单独实施。

## 确认的 V1 交付

1. 可安装 Python 包 `dce`、Typer CLI、独立 MCP Server。
2. 初始化 discover：扫描授权范围，解析模块、CI、镜像、Compose、Swarm。
3. 映射目录 Catalog：本地 SQLite、证据、关系版本、人工审批、差异检测。
4. BugContext 与 pipeline diagnose 的只读高层工具。
5. 合成 fixtures、离线 E2E、详细使用指南与内网只读 smoke 测试。

## 为什么用 CLI 优先

本项目最初目标是减少 Agent 工具轮次和 Token；V1 没有必要额外开发大型 Web UI。CLI 支撑本地人工审核，MCP 支撑 Cursor/Codex，后续内网共享可以增 FastAPI/前端。

## 当前决策

- 首版：Python 3.12+ / SQLite / MCP stdio；未来可迁移 PostgreSQL + 内网 HTTP。
- 仓库：`devops-context-engine`，先 Private、合规确认后再公开。
- 研发：按照 `specs/001-dce-v1/tasks.md` 的 T0–T7 运行，长任务要留本地阶段记录。
