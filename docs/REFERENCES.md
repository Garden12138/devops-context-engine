# 官方资料与技术参考（2026-10 核对）

以下链接供工程实现时验证 API 细节；自建实例的真实版本与能力最终以只读 `probe()` 的结果为准：

- ZenTao REST v1 Token 和权限：https://www.zentao.net/book/api/1397.html
- GitLab REST API：https://docs.gitlab.com/api/rest/
- GitLab Pipelines API：https://docs.gitlab.com/api/pipelines/
- GitLab Jobs Trace：https://docs.gitlab.com/api/jobs/
- Portainer API 文档：https://api-docs.portainer.io/
- Portainer Stack/ Git redeploy 接口（V2 预研，V1 不调用）：https://github.com/portainer/portainer-skills/blob/main/portainer-api/references/stacks.md
- MCP Python SDK：https://github.com/modelcontextprotocol/python-sdk
- Cursor Project Rules / AGENTS.md：https://docs.cursor.com/context/rules-for-ai
- Codex Goals (`/goal`，需支持的 Codex build)：https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- Codex 长任务阶段记录：https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex
- GitHub CLI 创建仓库：https://cli.github.com/manual/gh_repo_create
- GitHub Rulesets：https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository

## 实现提醒

- 文档接口只是示例；不要依靠未经本地验证的 API schema 写高风险操作。
- GitLab Self-Managed、ZenTao 旧版和 Portainer CE/BE 存在差异，需能力探测 + Mock 测试。
- 当前 V1 只读，不调用任何会改变公司环境的 endpoints。
