# 版本记录

## v2.0.0

DCE 2.0 是面向 Cursor 和 Codex 的 MCP 工具集，串联禅道、GitLab 和 Portainer，完成测试环境的缺陷修复闭环。

### MCP 工具

- `project_setup`
- `dce_status`
- `bug_list`
- `bug_get`
- `deploy_plan`
- `merge_to_test`
- `ci_build`
- `ci_status`
- `service_deploy`
- `service_status`
- `run_update`
- `bug_resolve`

### 与 1.x 不兼容的变化

- 移除全部 1.x 工具和项目模式审批。项目配置改用业务工作区的 `.dce/dce.yaml`，人工确认通过 Playbook 和宿主的工具调用确认完成。
- GitLab 个人访问令牌需要 `api` scope。

### 已知限制

- Portainer 不支持 `forceupdateservice` 时回退到 Docker 服务更新，使用有效的构建 digest 固定镜像。
- Cursor CLI 和 Grok Bot 的无界面场景尚未验证。
- 闭环仅覆盖测试环境。
