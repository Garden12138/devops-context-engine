# DCE 2.0 文档索引

DCE 2.0 是给 Cursor / Codex 用的 MCP 工具集，支撑“禅道缺陷 → 修复 → 合并 → CI → Portainer 部署 → 测试 → 记录 → 禅道已解决”的闭环。它持有平台凭证，提供 12 个按闭环步骤划分的工具。Agent 按 Playbook 编排，用户只在修复方案和合并前两处确认。

## 阅读顺序

| 文档 | 内容 | 谁要读 |
|---|---|---|
| [01-诊断与重构决策](01-诊断与重构决策.md) | 1.x 为什么失败、2.0 的决定、保留/删除清单、刻意不做的事 | 所有人 |
| [02-需求规格](02-需求规格.md) | 角色分工、闭环步骤、功能需求、人工停点、成功标准 | 所有人 |
| [03-架构设计](03-架构设计.md) | 目录结构、配置与凭证、运行记录、扫描/计划/合并/构建/部署/缺陷算法、安全模型、错误与返回结构 | 实现者 |
| [04-工具契约](04-工具契约.md) | 12 个 MCP 工具的输入输出、CLI 对照 | 实现者 |
| [05-实施计划](05-实施计划.md) | M0–M5 里程碑、任务、测试场景、给 Codex 的启动提示 | 实现者 |
| [06-验收标准](06-验收标准.md) | 离线验收、R1–R5 现场验收、旧痛点回归清单 | 用户、实现者 |
| [07-Playbook](07-Playbook.md) | Agent 标准操作（SKILL.md 正文）与修复记录模板 | 用户、Agent |
| [08-使用指南](08-使用指南.md) | 安装、宿主连接、初始化和日常操作 | 用户 |
| [CODEX_HANDOFF](CODEX_HANDOFF.md) | 交给 Codex 的执行规则，以及每个里程碑可直接粘贴的提示 | 用户、Codex |

实施进度记录在 [progress.md](progress.md)。

## 一页纸摘要

- **工具（12 个）**：`project_setup`（scan/check）、`dce_status`、`bug_list`、`bug_get`、`deploy_plan`、`merge_to_test`、`ci_build`、`ci_status`、`service_deploy`、`service_status`、`run_update`、`bug_resolve`。
- **配置**：业务工作区的 `.dce/dce.yaml`，由 scan 生成、用户在编辑器里修改，记录仓库 → 测试分支 → CI job → 镜像 → Portainer 服务的约定。没有关系状态机。
- **运行记录**：`.dce/runs/<run_id>.json`，保存计划、合并、构建、部署、验证、记录、禅道结果，供新会话恢复。
- **工作区绑定**：项目级 `.cursor/mcp.json` 传 `--workspace ${workspaceFolder}`，不再依赖 MCP Roots。
- **写操作**：7 条固定写接口白名单，目标必须在配置内，只覆盖测试环境；不 force push，不碰 master/release/prod/uat。
- **确认点**：G1 修复方案（缺陷不清楚或改动大时）、G2 合并前。宿主中 `merge_to_test` 不设为自动运行。
- **禅道终点**：“已解决”，指派回提测人，由测试关闭。
