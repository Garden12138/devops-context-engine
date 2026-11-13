# Cursor Agent 改造提示词

请在当前 DCE 仓库中，根据 `docs/refactor/agent-led-initialization/CHANGE_PROPOSAL.md` 和 `docs/refactor/agent-led-initialization/specs/` 完成 Agent-led Project Initialization 架构改造。

- DCE 负责三平台只读连接、结构化查询、文件/图片/日志证据。
- 当前 Cursor/Codex Agent 负责读取目标业务项目、推理禅道/GitLab/Portainer 关系、询问用户并维护当前项目 `.dce/project.yaml`。
- 不再让 DCE 内部模型或全局关系引擎负责业务项目初始化。

先审计当前真实代码和六个 MCP 工具，不要猜名称。保留已验收 Adapter、MCP、只读能力和兼容接口。按 `docs/refactor/agent-led-initialization/specs/06-security-and-migration.md` 的 T0-T7 推进。实现 Schema/校验、项目隔离、多对多、证据和人工审核。原全局关系目录先备份并降级，不能粗暴删除。V1 仍然只读，不实现构建/部署/平台写操作。每阶段运行测试并更新 harness 记录。最终提供架构变化、兼容性、测试证据和未完成事项。
