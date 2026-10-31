# V1.0 执行总计划（长任务的唯一状态入口）

## 阶段定义

| 顺序 | 阶段 | 可交付产物 | 验收门槛 |
|---|---|---|---|
| T0 | 项目初始化 | 包管理、lint/typecheck/test、CLI 入口、配置与脱敏 | 离线测试启动成功 |
| T1 | Adapter | ZenTao/GitLab/Portainer 只读接口 | 模拟服务测试 + 错误/分页/授权测试 |
| T2 | Discovery | Repo/Module/CI/Compose/Swarm 解析 | 合成多模块、多服务、历史 Stack 场景通过 |
| T3 | Catalog | Entity/Edge/Evidence/Snapshot/ScanRun/Review 持久化 | 迁移、幂等、版本、去重测试通过 |
| T4 | Mapping | 规则关联 + AI 可选候选 + 审核 | 不自动确认模糊关系，证据可追溯 |
| T5 | CLI | init/discover/catalog/trace/bug context/mapping review | CLI 契约、退出码与安全输出通过 |
| T6 | MCP | 只读工具，CLI 共用服务层 | MCP 离线集成契约、最小输出验证 |
| T7 | E2E 与文档 | fixtures、测试报告、内网 smoke 指南 | 所有 P0、质量门槛、无泄密 |

## 运行纪律

当前进度（2026-10-31）：T0–T2 passed，T3 implementing；本地分支 `work/dce-v1-offline`。
T2 完成时：79 tests、97.41% 分支覆盖率、ruff、strict mypy 已通过。

- 一次只推进一个阶段，测试不过不跳阶段；阶段完成记录测试命令、退出码与摘要。
- 当前阶段以 `harness/build-log.md` 标记为准；每个阶段前更新进度；若不存在，创建它。
- 每阶段在 `harness/context/TN.md` 记录结构变化、关键假设、实施决策、待解决点。避免长上下文崩溃后失去信息。
- API 版本差异应先能力探测，不在未验证条件下假设某路由支持写操作。
- 每阶段可自动本地提交小批量代码；**禁止自动推送、改动公司 GitLab/Portainer/ZenTao 资源**。
- 若涉及需要人工批准的操作：创建待办/阻塞记录并推进其他安全任务；不得绕过权限。

## 约定

- 以 `.env.example` 为示例，真实配置 `.env` gitignored。
- AI Provider 默认关闭；无 API Key 时规则发现和人工审核仍可用。
- 真正的自动构建/部署在 V1.2/V2.0 单独规划，不因为长任务执行就提前实现。
- 即使对话因环境/额度中断，后续只需将 `prompts/RESUME.md` 发给 Agent。
