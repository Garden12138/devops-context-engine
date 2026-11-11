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

## 公开验收场景与本地证据边界

公开示例和fixtures全部使用合成身份，不保存公司项目、缺陷、仓库、Stack、Swarm或CI任务的真实标识。真实样本只在用户明确授权的本地受保护目录取证，不复制到本资料包。

- ZenTao缺陷与图片场景验证内容和权限边界；Project、Product和Bug使用各自的来源实例与资源ID。
- 业务源码仓库与部署配置仓库分别取证，不因名称、默认分支或数字ID相似自动绑定。
- Stack保存信息、当前Swarm身份及Service namespace必须独立核对；不匹配只说明当前关联缺少证据，不推定环境已废弃。
- GitLab当前配置、Stack保存配置与运行服务分别保留来源；不能只凭服务数量认定相同版本。
- 图片、Compose和失败Job/Trace仅在单独授权的本地范围验证；不可访问或已过期时如实记录，不编造响应或部署事实。

本次改造保持 V1 只读，不引入构建、平台写入或部署能力。不得把 Token 写入项目关系文件。
