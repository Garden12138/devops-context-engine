# Cursor 复验与批准后的项目文件落地 — 2026-11-04

用户回传了实际 Cursor Agent 的两次复验，并明确允许保存完整草案、要求不要提交。本轮仅记录证据和由 Codex Host 创建已批准的业务文件；无新的平台调用，不运行 git add/commit/push，不修改已记录关系状态或审批字段。

## 用户回传的真实 Host 证据

- Bug 查询文本为 JSON 信封，status=ok，信封和 data.truncated 均 false，source.operation=bug。data.evidence 有 1 条；顶层 evidence 为空。事实工具以 data.evidence 提供结构化证据，顶层数组为旧兼容 evidence ID 字段；不把顶层空数组解读为无证据。
- 图片查询的原生 MCP ImageContent 实际进入 Cursor 模型可见内容，MIME=image/png，image_delivery=delivered，truncated=false。用户提供非敏感外观判断，说明是应用界面截图；未保存或转录图片。
- 先前九工具、三次真实调用、当前项目初始化对话和明确 unresolved 原因保留。原先那三次调用的 truncated 仍是 not_observable，不用新一次结果覆盖历史事实。

上述内容标为 user_reported_actual_cursor_agent_recheck；与 SDK 原生协议成功分开记录，不声称当前执行器直接观察了 Cursor 窗口或图像。

## 文件保存与验证

保存前核对了目标业务目录及其上级/目标目录 AGENTS 规则；目标没有已有 project.yaml，也无 .dce symlink。完整草案 683 行/23 关系，与已展示的完整 diff 逐字匹配，先经 Schema 校验，检查 Git roots 均位于目标 workspace 内。

Codex Host 以只创建新文件的方式写入业务 `.dce/project.yaml`，拒绝覆盖及 symlink，文件 0600；22451 字节，与批准草案逐字一致。DCE 服务本身不具备业务目录写接口。

- 实际 `dce project validate <已授权 workspace> --workspace-id <实际 ID>` exit 0。
- 通过 load_project 复读，模型与批准的源文档一致，所有 roots 都在该业务工作区内。
- 关系 22 proposed、1 unresolved、0 confirmed；所有 approved_by/approved_at 仍为空。用户批准保存文件没有被当作逐条关系确认。
- 业务 Git HEAD 和 index 的摘要在操作前后均未变，新文件为 untracked。未执行 git add/commit/push；本轮 DCE 文档/报告修改也不提交。
- 保存回执的路径、内容指纹和私有实例事实仅在 gitignored intake 目录。公开报告只记计数/状态，不包含业务拓扑、真实图像或凭证。

## 当前完成范围

核心 Agent-led 初始化链路已有真实证据：Host 连接/枚举/三平台实际调用、JSON 文本消费、真实图片到模型、本地项目理解、候选和未知关系、用户看 diff 后批准、业务项目文件落地/校验/复读。维护状态/隔离/多对多/刷新仍以既有离线测试和纯刷新证据为准，不杜撰新一轮平台刷新。

离线基线仍为 208 tests passed、覆盖率 97.93%，本轮无产品代码修改，不重复全库测试或真实请求。完整模块树仍因 403 Access not allowed 未取得；旧独立 GitLab 样本/仓库 Compose 的本轮范围未获明确授权，仍 not_verified，严格全样本验收未完成，不标 goal complete。禁止把当前文件保存批准扩大解释为旧平台样本授权。


收尾：目标业务文件另经独立 JSON Schema 校验通过；文档工作流 2 passed（0.79s），8 份文档相对链接零缺失，11 个公开工作区文件私有路径/站点扫描通过，git diff --check 通过。DCE HEAD 未变、暂存区为空；没有 git add/commit/push。
