# 当前目标 — Agent-led Project Initialization

本轮以 docs/refactor/agent-led-initialization/dce-agent-led-refactor/CHANGE_PROPOSAL.md 与 specs/01–07 为准。

1. DCE 是模型无关只读能力层，提供三平台连接、范围查询、分页、错误、脱敏、预算与证据/原生图片内容。
2. Host 在指定业务工作区读取本地上下文，推理多对多候选、解释冲突、取得用户审核并维护 .dce/project.yaml；DCE 不直接写业务仓库。
3. confirmed 需证据和真实人工审批，环境归属不凭名称；刷新保留审批/备注/拒绝，新关系 proposed，证据变化 stale/conflicted。
4. 全局 Catalog 先备份再降级为资源缓存/历史；保留旧消费者，不自动把旧 confirmed 导入项目。
5. 离线单元/契约/E2E、安全、隔离与多对多检查通过；至少一个真实 Host 完成 connect/list/三次真实只读调用和当前项目初始化对话，并确认一条关系或明确 unresolved。
6. 未验证的版本接口、图片到模型与外部事实保留 not_verified，不能以历史证据/合成数据替代。

当前离线 208 tests passed、总体覆盖率 97.93%，ruff/strict mypy 通过。三平台真实读取和旧库副本迁移有证据；用户已回传 Cursor connect/list/三次实际调用及初始化对话，但旧文本仅 DCE result.、截断不可见。现已修复九工具 JSON 文本兼容；授权新样本原生 PNG 通过 SDK 验证。项目草案 22 proposed/1 unresolved/0 confirmed，完整 diff/校验/纯刷新通过，保存待用户批准；模块入口 403、Cursor 修复后文本/图片复验及旧独立样本补验仍待完成。详见 harness/agent-led-acceptance.md。

## 旧 V1 目标（历史兼容依据）


## 核心成果

1. 三平台可配置且可测试的 **只读** Adapter：ZenTao v1，GitLab REST v4，Portainer Stack + Docker Swarm API Proxy。
2. `dce init` 自动发现目标范围，能恢复、分页、缓存与增量更新；支持离线 fixtures 和本地模拟 API。
3. 针对 GitLab 单仓库多模块、多镜像、多服务、多环境建立关系，显式区分业务功能模块 / 代码 Module / Swarm Service。
4. 只在有证据时确认技术关系；对语义关联生成 AI 候选、证据与不确定性，由人工审核，结果持久化且可撤销。
5. `dce bug context <id>` 返回轻量统一摘要、附件的本地安全路径/受控引用、候选仓库与模块、映射状态和证据；MCP 复用核心逻辑。
6. 离线端到端测试通过，真实内网只读 smoke 检查有清晰步骤、最小权限和不泄密机制。

## 本版不做

- 不自动修复代码、不触发 Pipeline、不推送/合并 MR、不更新禅道状态、不执行 Portainer redeploy。
- 不替代 GitLab CI/CD、Portainer、禅道或 Coding Agent。
- 不假设所有模块皆可直接部署，不以名字自动决定生产/测试环境，不按 `latest` 判断镜像版本。
- 不做 Web 管理大平台、微服务集群、Neo4j、实时全量代码向量化或无限制爬取仓库。

## 核心完成定义

- 详见 `specs/001-dce-v1/acceptance.md` 的验收矩阵，所有 P0 通过。
- 无 Token/密码在输出、日志、测试快照、git diff 或公共仓库中泄漏。
- 80+% 核心代码单元测试覆盖率作为推荐目标，硬门槛：关键安全/状态/关系规则 100% 关键分支有测试；整体覆盖率不得低于 75%。
- 运行 `pytest`、`ruff check`、`mypy`（或 pyright，定下后保持一致）、CLI smoke、MCP 工具契约测试。
- 完整执行记录写入 `harness/build-log.md`，包含完成阶段、测试命令、结果、遗留问题；不伪称真实内网测试已经完成。
