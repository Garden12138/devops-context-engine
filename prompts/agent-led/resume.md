# Agent-led 重构续跑

先读根 AGENTS.md、README.md、GOALS.md、PLANS.md、harness/build-log.md、harness/test-results.md 和 harness/agent-led-acceptance.md。提案实际在 docs/refactor/agent-led-initialization/dce-agent-led-refactor/，核对 CHANGE_PROPOSAL.md 与 specs/01–07，以当前代码确认工具名/Schema/命令。

2026-11-05 增量 A–D 已完成：九工具名称保持，事实 revision 2.1；新增 project_jobs/branch_jobs/pipeline_bridges、stack_service；Project Context v1 可读/默认不变，显式 v2 typed details 和纯 migrate/CLI stdout 预览。最终 226 tests passed/97.63%，ruff/mypy49/stdio增量E2E/wheel隔离安装与限定真实SDK通过。实际业务文件当前24proposed/3unresolved/1confirmed，逐字指纹不变；不要按下方旧计数覆盖。真实新API调用为SDK，不声称Cursor已调用新operation；需重载现有连接后使用。实际示例在 .local/agent-led/incremental-v1/MCP_CALLS.md，报告在 harness/incremental-v1-acceptance.md。本轮不修改业务文件，不暂存/提交/推送，保留已有未提交变更。严格分开当前增量与下面历史目标，旧模块权限/独立样本不属于这次增量验证。

用户最新明确约束：允许保存完整项目草案，但不要提交。不要 git add/commit/push 业务项目文件或当前 DCE 记录变更；优先于旧阶段提交约定。不要再次索要已给出的业务工作区、凭证源、HTTP 授权、Cursor 选择、图片样本或文件保存批准。

本地分支 refactor/agent-led-project-init，查看 git status/log 并保留当前未提交文档记录，不覆盖用户变更。代码/离线基线 208 tests passed/97.93%，ruff/strict mypy（48 files）/最终 wheel 隔离检查通过；本轮没有产品代码修改，不重复全库测试或真实请求。

已完成的真实主链路：
- 三平台限定 SDK 读取、实际旧 Catalog 副本先备份后迁移并保留 191 实体/219 边/219 证据/11 快照。
- 用户回传 Cursor 九个 DCE 工具（另有 Host mcp_auth）、至少三次实际调用和业务工作区初始化对话；明确 Bug 代码归属 unresolved。
- 九工具 JSON 文本兼容已修复；用户最新复验确认 JSON 信封实际可见，Bug 信封/data.truncated 均 false，data.evidence 1 条。原先三次截断未知不回写为 false。
- 独立授权图片经 SDK 返回原生 PNG，用户再确认 MCP ImageContent 实际进入 Cursor 模型可见内容，image_delivery=delivered、truncated=false；不保存/转录图片。
- 完整 683 行/23 关系草案获批准后，由 Codex Host 以拒绝覆盖/symlink 的方式创建业务 .dce/project.yaml；CLI validate exit 0、load_project 复读及源字节一致性通过，22 proposed/1 unresolved/0 confirmed，审批字段全空。
- 业务 Git HEAD/index 保存前后不变，文件 untracked；无 git add/commit/push。DCE MCP 服务仍没有写业务目录能力。

业务文件路径和保存回执在 .local/agent-led/intake/project-save-receipt.json；候选原稿与 diff 保留。公开证据见 harness/context/agent-led/cursor-recheck-and-approved-save.md。后续 Host 维护读取已保存文件，保留 notes/审批/拒绝；新关系 proposed，证据变化 stale/conflicted，任何新修改先展示 diff 并取得相应授权。不要重复创建/覆盖现有项目文件，不把文件保存批准当作业务关系确认。

严格全样本验收剩余：
1. module_tree 真实返回 403 Access not allowed，同 Token Bug 200，登录正常。官方 modules→tree/browse→checkPriv 与错误相符，推断需实例管理员核对单独读入口/产品范围；实例版本未确认，权限未变化前不重复探测、不索取管理员 Token、不绕过。
2. 旧独立 GitLab Project/Pipeline/Job 与仓库 Compose 的本轮读取范围尚未获明确批准；自动审批曾在执行前拒绝，未经明确授权不重试。文件保存批准不扩展该范围。
3. 三份 Stack File 服务数 63/71/78、运行 namespace 8 页 78 个唯一 Service ID 为独立来源；GitLab Compose 未重验，不能复用旧 78 当当前事实。两个 Stack Swarm mismatch 保留候选；不确认环境/健康/版本。

更新 PLANS/build-log/test-results/验收与机器摘要，遵守不提交约束。核心初始化已通过，严格全样本验收仍未完成，不标 goal complete；不以旧报告或合成数据替代真实外部证据。
