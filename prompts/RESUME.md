> 当前 Agent-led 重构请先按 [agent-led/resume.md](agent-led/resume.md) 接续；以下旧 V1 流程仅供历史参考。

# 长任务续跑提示词（Codex / Cursor 通用）

```text
继续当前仓库的 DCE V1.0 开发。不要从头规划，不要只总结，也不要重做已验证的工作。

请先读取 AGENTS.md、GOALS.md、PLANS.md、specs/001-dce-v1/tasks.md、specs/001-dce-v1/acceptance.md、harness/build-log.md 和 harness/context/ 下最近一个阶段的记录；检查 git status、git log -5、实际代码与测试状态，确认上一次真正完成的阶段以及残余失败项。

以已有阶段成果为基线，从第一个未通过 P0 的任务继续：修改实现 → 运行相关测试 → 修复失败 → 写入实际证据 → 更新日志和小提交 → 继续下一个阶段。保持 V1 只读，默认 Mock，禁止对真实公司平台执行任何写操作、推送公开仓库或泄露密钥。

如果文档日志和真实代码/测试不一致，以可运行的证据为准，先修正日志。不足以完成 V1 时如实列出 blocker 和明确下一步，不要凭猜测宣布完成。
```

如果 Codex Goal 仍在同一线程且处于暂停状态，可先执行 `/goal resume`；若线程或 Goal 已不存在，以上提示词可作为新会话入口。
