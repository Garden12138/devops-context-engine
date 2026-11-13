# 当前 Agent-led 提示词

业务项目初始化与维护入口：prompts/agent-led/initialize.md、refresh.md、review.md、bug-context.md、service-trace.md、pipeline-diagnose.md；完整协议见 docs/AGENT_LED_WORKFLOW.md。DCE 不写业务目录。重构续跑见 prompts/agent-led/resume.md。

## 旧 V1 提示词（历史）

# 提示词索引

- **Codex 长任务**：`prompts/CODEX_LONG_TASK.md`
- **Cursor 长任务**：`prompts/CURSOR_LONG_TASK.md`
- **任务中断续跑**：`prompts/RESUME.md`

执行方式：进入新仓库根目录，打开 Codex CLI 或 Cursor Agent，复制对应 Markdown 文件的全文作为第一轮对话。Codex 支持 Goals 的版本（官方文档所述 >=0.128.0）建议用 `CODEX_LONG_TASK.md` 中的一条 `/goal` 设立可验证的 V1 目标；`/plan` 只做规划，不适合单独承担实现。若当前版本不支持 `/goal`，使用普通 Agent 会话加 build-log 续跑。

长任务不能保证跨会话或突破产品额度自行持续运行。依靠 `PLANS.md` + `harness/build-log.md` + 本地小提交实现可恢复。
