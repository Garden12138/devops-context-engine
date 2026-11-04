# Agent-led Project Initialization

当前契约：原六工具 revision 1.1 兼容，三个事实工具 revision 2.0。Host 持有源码上下文与模型，DCE 不调用模型、不写业务工作区、不拥有项目业务关系真相。

1. 在指定业务项目打开 Host，确认 workspace 绝对路径；先枚举 MCP。
2. 安全进程环境加载 DCE 平台配置，stdio 启动示例见 [工具说明](MCP_FACT_TOOLS.md)。凭证不放在项目 YAML 或聊天中。
3. 使用 [initialize](../prompts/agent-led/initialize.md)，按本地证据和允许范围查询。未配置平台明确记录 not_verified。
4. Host 展示候选、冲突、证据和 diff；用户审核后由 Host 写入 .dce/project.yaml。无批准时不产生 confirmed。
5. `dce project validate <workspace> --workspace-id <id>` 只读校验；重新读取核对。Schema/模板可用 `dce project schema`、`dce project template --workspace-id <id>` 输出到 stdout，DCE 不自动保存。
6. 维护使用 [refresh](../prompts/agent-led/refresh.md)、[review](../prompts/agent-led/review.md)、[bug-context](../prompts/agent-led/bug-context.md)、[service-trace](../prompts/agent-led/service-trace.md)、[pipeline-diagnose](../prompts/agent-led/pipeline-diagnose.md)。

纯 Python `dce.project.context.refresh(project, observations)` 返回候选文档，保留人工审核和拒绝；Host 负责差异展示、数据不可访问与资源删除的区分和用户授权。不需要在 DCE 内部注册模型供应商。

[Schema](../schemas/project.schema.json)、[模板](../examples/project-context/project.yaml)、[gitignore 片段](../examples/project-context/gitignore.txt)。节点包含来源实例；schema 中 implemented_by 兼容提案示例。运行时还检查 scope、秘密、重复 YAML key、路径与工作区隔离。审批元数据是可审核记录，不能单独证明人类身份。

Host 验收必须记录真实 Host、MCP connect/tools/list、至少三次真实只读工具调用、当前业务项目初始化对话及人工关系确认或 unresolved 原因。标准 SDK、合成平台、启动进程不能替代这一项。
