# 03 — 项目关系文件 Schema

## 文件布局
```text
business-project/
  .dce/
    project.yaml
    local.example.yaml
    local.yaml       # gitignore
    runs/            # 可选忽略
```

## project.yaml 示例
```yaml
schema_version: 1
workspace:
  id: "business-project"
  name: "Business Project"
  roots:
    - path: "."
      kind: "git_repository"
      remote_url: "http://gitlab.example/group/repo.git"
      default_branch: "master"
scope:
  zentao:
    instance: "company-zentao"
    projects: []
    products: []
  gitlab:
    instance: "company-gitlab"
    projects: []
  portainer:
    instance: "company-portainer"
    endpoints: []
    stacks: []
relationships:
  - id: "rel-001"
    from: {type: "zentao_project", id: "28"}
    relation: "implemented_by"
    to: {type: "gitlab_project", id: "123"}
    status: "proposed"
    confidence: 0.0
    evidence:
      - kind: "agent_analysis"
        source: "workspace-and-platform-metadata"
        locator: "run-001"
        observed_at: "2026-11-04T00:00:00Z"
        revision: null
        summary: "候选关系，等待用户确认"
    approved_by: null
    approved_at: null
    last_verified_at: null
    notes: ""
metadata:
  created_at: null
  updated_at: null
  initialized_by: "cursor"
  last_refresh_at: null
```

## 节点类型
`zentao_product`, `zentao_project`, `zentao_module`, `zentao_bug`, `gitlab_project`, `code_module`, `source_path`, `ci_pipeline`, `ci_job`, `container_image`, `deployment_repository`, `compose_file`, `compose_service`, `portainer_endpoint`, `portainer_stack`, `swarm_cluster`, `swarm_service`, `environment`。

## 关系状态
- `proposed`：Agent 提议，未确认。
- `confirmed`：用户/授权审核者确认。
- `rejected`：明确拒绝。
- `stale`：旧证据失效。
- `conflicted`：来源冲突。
- `unresolved`：证据不足。

`confidence` 不能替代 evidence 和人工审核。confirmed 必须有 evidence、approved_by、approved_at。

## 关系类型
`contains_module`, `implements`, `builds`, `produces_image`, `uses_image`, `declares_service`, `deployed_as`, `managed_by_stack`, `runs_in_environment`, `depends_on`, `related_to`。

## 存储策略
- `project.yaml` 不得含 Token/密码/API Key。
- 内部拓扑是否提交由公司安全策略决定。
- 若不能提交，使用本地/公司内部存储；不要推到公开仓库。
- 不保存完整截图、完整日志、环境变量或 Compose secret。
