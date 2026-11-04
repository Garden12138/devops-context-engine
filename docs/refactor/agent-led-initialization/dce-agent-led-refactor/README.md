# DCE Agent-led Project Initialization Refactor

本资料包指导现有 DCE 从“DCE 自己发现并推理公司级关系”改为“接入的 Agent 在当前业务项目中完成初始化和关系维护”。

## 新定位
**DCE 是平台能力与证据提供层；Cursor/Codex 等 Agent 是项目关系的分析者和维护者。**

- DCE：连接禅道、GitLab、Portainer；提供安全只读 API/MCP、结构化数据、文件/图片/日志证据、分页、错误处理和脱敏。
- Agent：读取当前 workspace、本地源码和配置；调用 DCE；推理项目关系；向用户确认；维护当前项目 `.dce/project.yaml`。
- 用户：确认业务语义、环境归属和不确定关系。

## 阅读顺序
1. `CHANGE_PROPOSAL.md`
2. `specs/01-requirements.md`
3. `specs/02-architecture.md`
4. `specs/03-project-context-schema.md`
5. `specs/04-mcp-contract.md`
6. `specs/05-agent-workflow.md`
7. `specs/06-security-and-migration.md`
8. `specs/07-acceptance.md`
9. `prompts/CODEX_REFACTOR_LONG_TASK.md`
10. `prompts/CURSOR_REFACTOR_TASK.md`
11. `prompts/AGENT_PROJECT_INITIALIZATION.md`
12. `prompts/PROJECT_CONTEXT_MAINTENANCE.md`

## 已知真实样本（仅作验收数据，不得硬编码）
- 禅道 Bug 4314：项目 ID 28，项目名“博今智推3.0”，产品 ID 13；曾有两张 PNG 图片附件。
- GitLab `bjps/link-forge`：Project ID 314，默认分支 master。
- GitLab `devops/portainer`：Project ID 151，默认分支 master。
- Portainer Stack 19/21/31 分别为 `bjzt_3_0`、`bjzt_3_0_test`、`bjzt_3_0_new`。
- Endpoint 1 当前 Swarm ID 曾为 `061j0zbg8sckbgfqqzg9oxc19`；Stack 31 匹配，Stack 19/21 不匹配。只能称“不匹配当前集群/历史候选”，不能认定已废弃。
- GitLab master Compose 曾解析出 78 个 service；Stack 21 保存 Compose 曾有 71 个；当前 namespace `bjzt_3_0_new` 曾查询到 78 个 Swarm Service 对象。这是三个不同来源观察值，不能只看数量判断配置相同。
- Stack 31 保存的 Compose 仍需单独读取后才能与 GitLab master 逐项比较。
- GitLab Project 314 的 Pipeline 22154 / Job 63820 曾存在失败日志；验收时必须重新检查是否仍可访问。
- 不得假定 `link-forge` 与禅道 Bug 4314 属于同一个业务项目。

本次改造保持 V1 只读，不引入构建、平台写入或部署能力。不得把 Token 写入项目关系文件。
